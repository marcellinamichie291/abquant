from abquant import trader
from datetime import datetime
import threading
from typing import Dict, List
import argparse
import time
from pprint import pprint

from abquant.trader.tool import BarGenerator
from abquant.trader.common import Exchange, OrderType
from abquant.trader.utility import generate_ab_symbol, round_up
from abquant.event.event import EventType
from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.event import EventDispatcher, Event
from abquant.gateway import BinanceUBCGateway, BinanceBBCGateway

from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import SubscribeMode


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', type=str, required=True,
                        help='api key')
    parser.add_argument('-s', '--secret', type=str, required=True,
                        help='secret')
    parser.add_argument('-u', '--proxy_host', type=str,
                        # default='127.0.0.1',
                        help='proxy host')
    parser.add_argument('-p', '--proxy_port', type=int,
                        help='proxy port')
    args = parser.parse_args()
    return args


class TheStrategy(StrategyTemplate):
    param1 = None
    param2 = None
    trade_flag = False
    check_pos_interval = 20
    balance = 10000

    parameters = [
        "param1",
        "param2",
        "trade_flag",
        "check_pos_interval",
        "balance"
    ]
    variables = [
    ]

    def __init__(
        self,
        strategy_engine: LiveStrategyRunner,
        strategy_name: str,
        ab_symbols: List[str],
        setting: dict
    ):
        """"""

        super().__init__(strategy_engine, strategy_name, ab_symbols, setting)
        self.bgs: Dict[str, BarGenerator] = {}
        self.last_tick_time = None

    def on_init(self):
        for ab_symbol in self.ab_symbols:
            self.bgs[ab_symbol] = BarGenerator(lambda bar: None, interval=5)

        # init时 从交易所获取过去n 天的1 分钟k线。生成 60 * 24 个供 strategy.on_bars 调用的 bars: Dict[str, BarData], 字典的key是 ab_symbol, value是BarData.
        # 从交易所获取后，顺序调用on_bars 60 * 24 次，再返回。
        # 由于是strategy实例尚未 start，因此在on_bars中调用的下单请求，不会发送，同时处理回报的update_order/trade 方法也不会被调用。
        # 即load_bars 方法适用于 需要根据历史k线预热的策略。 比如计算3日均线。使用该方法，可以避免strategy实例，上线后预热3日后正式开始交易。
        n = 1
        self.load_bars(n)
        self.write_log("策略初始化")

    def on_start(self):
        self.write_log("策略启动")

    def on_stop(self):
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        if (
            self.last_tick_time and
            tick.datetime > self.last_tick_time and
            self.last_tick_time.minute != tick.datetime.minute
        ):
            bars = {}
            for ab_symbol, bg in self.bgs.items():
                bars[ab_symbol] = bg.generate()
            # 生成新的k线数据后，主动调用 on_bars。
            self.write_log("new minutes tick: {}".format(tick))
            self.on_bars(bars)

        bg: BarGenerator = self.bgs[tick.ab_symbol]
        bg.update_tick(tick)
        if self.last_tick_time:
            self.last_tick_time = tick.datetime if tick.datetime > self.last_tick_time else self.last_tick_time
        else:
            self.last_tick_time = tick.datetime

    def on_bars(self, bars: Dict[str, BarData]):
        print("BARS: ")
        pprint(bars)
        
        if self.trade_flag:
            self.write_log("BARS, timestamp:{}, thread: {}, last_time: {}".format(
            datetime.now(), threading.get_native_id(), self.last_tick_time))
 
            self.write_log("activate orders: {}".format(self.active_orderids))
            for ab_orderid in self.active_orderids:
                self.cancel_order(ab_orderid)

            # 平仓 
            for pos_ab_symbol, pos_volume in self.pos.items():
                if pos_volume == 0:
                    continue
                elif pos_volume > 0:
                    # 平多
                    self.sell(pos_ab_symbol, bars[pos_ab_symbol].close_price, abs(pos_volume), OrderType.MARKET)
                else:
                    # 平空
                    self.cover(pos_ab_symbol, bars[pos_ab_symbol].close_price, abs(pos_volume), OrderType.MARKET)

            # 开新仓
            u_per_trade = 10
            trade_instrument = self.ab_symbols[0]
            trade_instrument_min_volumn = 0.001
            trade_price = bars[trade_instrument].close_price * (1 - 0.001)
            # 不用太担心，abquant会在发送订单前，自动检查 金融产品的 price_tick, 因此，如果你不知道该产品的price_tick，或下单的仓位较大，不用担心，下一行代码 可以不使用round_up.该操作是为高频小仓位的策略，精确控制仓位存在的。
            trade_volume = round_up(u_per_trade / trade_price, target=trade_instrument_min_volumn)
            self.buy(self.ab_symbols[0], price=trade_price, volume=trade_volume, order_type=OrderType.LIMIT)
            self.write_log(f"buy {self.ab_symbols[0]}, in price {trade_price}, with vol {trade_volume}")

            if len(self.ab_symbols) >= 2:
                u_per_trade = 10
                trade_instrument = self.ab_symbols[1]
                trade_instrument_min_volumn = 0.001
                trade_price = bars[trade_instrument].close_price  * (1 + 0.001)
                # 不round， 则最小成交单位交由abquant处理。
                trade_volume = u_per_trade / trade_price
                self.short(self.ab_symbols[1], price=trade_price, volume=trade_volume, order_type=OrderType.LIMIT)
            self.write_log(f"short {self.ab_symbols[1]}, in price {trade_price}, with vol {trade_volume}")
        # self.write_log(bars)
        # pprint({k:v for k, v in bars.items() if v is not None})
        # print("\n\n\n\n")

    def on_entrust(self, entrust: EntrustData) -> None:
        pass

    def on_transaction(self, transaction: TransactionData) -> None:
        # print(self.strategy_name, transaction)
        pass

    def on_depth(self, depth: DepthData) -> None:
        # print(self.strategy_name, depth.ab_symbol, depth.ask_prices)
        pass

    def on_exception(self, exception: Exception) -> None:
        print("EXCEPTION" + str(exception))

    def on_timer(self, interval: int) -> None:
        # 根据 event dispatcher的 interval 决定， 默认1秒调用一次。
        
        pass

    def update_trade(self, trade: TradeData) -> None:
        super().update_trade(trade)
        self.write_log("pos update: {} filled with {}. #trade details: {}".format(
            trade.ab_symbol, self.pos[trade.ab_symbol], trade))

    def update_order(self, order: OrderData) -> None:
        super().update_order(order)
        self.write_log("order still active: {}".format(self.active_orderids))
        self.write_log("order {}, status: {}. #order detail: {}".format(
            order.ab_orderid, order.status, order))


def main():
    args = parse()
    binance_setting = {
        "key": args.key,
        "secret": args.secret,
        "session_number": 3,
        # "127.0.0.1" str类型
        "proxy_host": args.proxy_host if args.proxy_host else "",
        # 1087 int类型
        "proxy_port": args.proxy_port if args.proxy_port else 0,
        "test_net": ["TESTNET", "REAL"][1],
    }

    event_dispatcher = EventDispatcher(interval=1)
    event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
        str('LOG: ') + str(event.data.time) + str(event.data)))
    event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(
        str('ACCOUNT: ') + str(event.data)))  # pass accessor,  trade_listerer not done
    # event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data))) # pass
    event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(
        str('POSITION: ') + str(event.data))) 

    binance_ubc_gateway = BinanceUBCGateway(event_dispatcher)
    binance_ubc_gateway.connect(binance_setting)
    binance_bbc_gateway = BinanceBBCGateway(event_dispatcher)
    binance_bbc_gateway.connect(binance_setting)

    time.sleep(3)
    subscribe_mode = SubscribeMode(
        # 订阅 深度数据 depth. 除非重建orderbook，否则不开也罢。
        depth=False,
        # 订阅最优五档tick
        tick_5=False,
        # 订阅best bid/ask tick
        best_tick=False,
        # 订阅委托单（通常不支持） entrust
        entrust=False,
        # 订阅交易数据 transaction, 自动生成 tick.
        transaction=True
    )

    # 有默认值，默认全订阅, 可以不调用下面两行。
    binance_ubc_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)
    binance_bbc_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)

    strategy_runner = LiveStrategyRunner(event_dispatcher)
    from abquant.gateway.binancec import symbol_contract_map
    ab_symbols = [generate_ab_symbol(
        symbol, exchange=Exchange.BINANCE) for symbol in symbol_contract_map.keys()]
    # this is subscribe all
    print("{} instrument symbol strategy0 subscribed: ".format(
        len(ab_symbols)), ab_symbols)
    # strategy_runner.add_strategy(strategy_class=TheStrategy,
    #                              strategy_name='the_strategy0',
    #                              ab_symbols=ab_symbols,
    #                              setting={"param1": 1, "param2": 2}
    #                              )
    strategy_runner.add_strategy(strategy_class=TheStrategy,
                                 strategy_name='the_strategy1',
                                 ab_symbols=["BTCUSDT.BINANCE",
                                             "ETHUSDT.BINANCE"],
                                 setting={"param1": 1, "param2": 2}
                                 )
    strategy_runner.add_strategy(strategy_class=TheStrategy,
                                 strategy_name='the_strategy2',
                                 ab_symbols=["BTCUSD_PERP.BINANCE",
                                             "ETHUSD_PERP.BINANCE"],
                                 setting={"param1": 3, "param2": 4}
                                 )
    # strategy_runner.add_strategy(strategy_class=TheStrategy,
    #                              strategy_name='the_strategy3',
    #                              ab_symbols=["XRPUSDT.BINANCE",
    #                                          "ICPUSDT.BINANCE"],
    #                              setting={"param1": 3, "param2": 4, "trade_flag": True}
    #                              )
    strategy_runner.init_all_strategies()

    # 策略 start之前 sleepyiduanshijian

    time.sleep(5)
    strategy_runner.start_all_strategies()

    import random
    while True:
        # renew strategy1 setting.
        time.sleep(5)
        the_strategy1_setting = {"param1": 2,
                                 "param2": 2 * random.uniform(0, 1)}
        strategy_runner.edit_strategy(
            strategy_name='the_strategy1', setting=the_strategy1_setting)
        # renew strategy2 setting.
        the_strategy2_setting = {"param1": 4,
                                 "param2": 4 * random.uniform(0, 1),
                                }
        strategy_runner.edit_strategy(
            strategy_name='the_strategy2', setting=the_strategy2_setting)


    # print([c.func.id for c in ast.walk(ast.parse(inspect.getsource(TheStrategy))) if isinstance(c, ast.Call)])
if __name__ == '__main__':
    main()
    # test()
