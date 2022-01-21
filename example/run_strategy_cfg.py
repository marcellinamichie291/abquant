import os, time
from typing import Dict, List
import pathlib

from abquant.event import EventDispatcher
from abquant.event.event import EventType
from abquant.gateway import BinanceUBCGateway, BinanceBBCGateway
from abquant.gateway.binances.binancegateway import BinanceSGateway
from abquant.monitor import Monitor
from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.trader.common import Exchange, OrderType
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import SubscribeMode
from abquant.trader.tool import BarAccumulater, BarGenerator
from abquant.trader.utility import generate_ab_symbol, round_up
from abquantui.config_helpers import parse_yaml
from abquantui.encryption import encrypt, decrypt


# 策略的实现，所有细节都需要明确。务必先看完.
class TheStrategy(StrategyTemplate):
    # 一下类属性/成员， 均由交易员自行决定并声明。
    param1 = None
    param2 = None
    trade_flag = False
    check_pos_interval = 20
    balance = 10000
    window = 2

    # 声明可配置参数，本行之上是可配置参数的默认值。
    parameters = [
        "param1",
        "param2",
        "trade_flag",
        "check_pos_interval",
        "balance",
        "window"
    ]
    # 声明未来可能出现的，可能需盘中纪录的可计算参数， 如需监控的因子值，以及各金融产品的仓位变化等等， 后续提供支持。
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
        self.bar_accumulator: BarAccumulater = None
        self.last_tick_time = None

    def on_init(self):
        for ab_symbol in self.ab_symbols:
            self.bgs[ab_symbol] = BarGenerator(lambda bar: None)
        # 聚合 bars 生成 window_bars， 根据k线生成 比如window分钟k线的barData， 并且调用 on_window_bars 回调函数。
        self.bar_accumulator = BarAccumulater(
            window=self.window, on_window_bars=self.on_window_bars)

        # init时 从交易所获取过去n 天的1 分钟k线。生成 60 * 24 个供 strategy.on_bars 调用的 bars: Dict[str, BarData], 字典的key是 ab_symbol, value是BarData.
        # 从交易所获取后，顺序调用on_bars 60 * 24 次，再返回。
        # 由于是strategy实例尚未 start，因此在on_bars中调用的下单请求，不会发送，同时处理回报的update_order/trade 方法也不会被调用。
        # 即load_bars 方法适用于 需要根据历史k线预热的策略。 比如计算3日均线。使用该方法，可以避免strategy实例，上线后预热3日后正式开始交易。
        n = 1
        self.load_bars(n)
        self.write_log("Strategy initiated")

    def on_start(self):
        self.write_log("Strategy started")

    def on_stop(self):
        self.write_log("Strategy stopped")

    def on_tick(self, tick: TickData):
        # 以下的代码是根据tick数据，生成 bars数据的代码。如果策略是分钟级，则不要做任何修改。
        if (
            self.last_tick_time and
            tick.datetime > self.last_tick_time and
            self.last_tick_time.minute != tick.datetime.minute
        ):
            bars = {}
            for ab_symbol, bg in self.bgs.items():
                bars[ab_symbol] = bg.generate()
            # 生成新的k线数据后，主动调用 on_bars。
            # self.write_log("new minutes tick: {}".format(tick))
            if all(bars.values()):
                self.on_bars(bars)

        bg: BarGenerator = self.bgs[tick.ab_symbol]
        bg.update_tick(tick)
        if self.last_tick_time:
            self.last_tick_time = tick.datetime if tick.datetime > self.last_tick_time else self.last_tick_time
        else:
            self.last_tick_time = tick.datetime

    def on_bars(self, bars: Dict[str, BarData]):
        # 生成出来的 bars，是所有订阅金融产品的 ab_symbol 与k线 数据的键值对。
        # 分钟级策略逻辑在这里实现， 注意策略里面不得出现任何 IO操作IO操作请使用strategyTemplate提供的接口。所有startegyTemplate提供的接口以下代码都有使用。 如 write_log, sell, buy, short, cover。

        # 更新window_bar生成器， 方便生成 n分钟k线。
        self.bar_accumulator.update_bars(bars)

        if self.trade_flag:
            # self.write_log("BARS, timestamp:{}, thread: {}, last_time: {}".format(
            #     datetime.now(), threading.get_native_id(), self.last_tick_time))

            # self.write_log("activate orders: {}".format(self.active_orderids))
            for ab_orderid in self.active_orderids:
                self.cancel_order(ab_orderid)

            # 平仓  self.pos存储的是该策略实例维护的仓位。
            for pos_ab_symbol, pos_volume in self.pos.items():
                if pos_volume == 0:
                    continue
                elif pos_volume > 0:
                    # 平多
                    self.sell(pos_ab_symbol, bars[pos_ab_symbol].close_price, abs(
                        pos_volume), OrderType.MARKET)
                else:
                    # 平空
                    self.cover(pos_ab_symbol, bars[pos_ab_symbol].close_price, abs(
                        pos_volume), OrderType.MARKET)

            # 开新仓
            u_per_trade = 10
            trade_instrument = self.ab_symbols[0]
            trade_instrument_min_volumn = 0.001
            trade_price = bars[trade_instrument].close_price * (1 - 0.01)
            # 不用太担心，abquant会在发送订单前，自动检查 金融产品的 price_tick, 因此，如果你不知道该产品的price_tick，或下单的仓位较大，不用担心，下一行代码 可以不使用round_up.该操作是为高频小仓位的策略，精确控制仓位存在的。
            trade_volume = round_up(
                u_per_trade / trade_price, target=trade_instrument_min_volumn)
            self.buy(self.ab_symbols[0], price=trade_price,
                     volume=trade_volume, order_type=OrderType.LIMIT)
            self.write_log(
                f"buy {self.ab_symbols[0]}, in price {trade_price}, with vol {trade_volume}")

            if len(self.ab_symbols) >= 2:
                u_per_trade = 10
                trade_instrument = self.ab_symbols[1]
                trade_instrument_min_volumn = 0.001
                trade_price = bars[trade_instrument].close_price * (1 + 0.01)
                # 不round， 则最小成交单位交由abquant处理。
                trade_volume = u_per_trade / trade_price
                self.short(self.ab_symbols[1], price=trade_price,
                           volume=trade_volume, order_type=OrderType.LIMIT)
            self.write_log(
                f"short {self.ab_symbols[1]}, in price {trade_price}, with vol {trade_volume}")

        if self.trading:
            self.write_log(bars)
        # pprint({k:v for k, v in bars.items() if v is not None})
        # print("\n\n\n\n")

    def on_window_bars(self, bars: Dict[str, BarData]):
        # window分钟级策略在这里实现， 注意设置 window参数。方便
        # self.write_log("WINDOW BAR: {}".format(bars))

        # 如果需要报警功能，配置好 monitor后可以通过该方法实现。
        self.notify_lark("send msg to lark")
        pass

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
        # 成交发生的回调。 可参考父类实现的注释。
        super().update_trade(trade)
        self.write_log("pos update: {} filled with {}. #trade details: {}".format(
            trade.ab_symbol, self.pos[trade.ab_symbol], trade))

    def update_order(self, order: OrderData) -> None:
        # 订单状态改变发生的回调。
        super().update_order(order)
        self.write_log("order still active: {}".format(self.active_orderids))
        self.write_log("order {}, status: {}. #order detail: {}".format(
            order.ab_orderid, order.status, order))


def main():
    parent_path = pathlib.Path(__file__).parent
    config_path = parent_path.joinpath('run_strategy.yaml')

    config = parse_yaml(config_path)
    gw_name = 'BINANCEUBC'
    gw_conf = config.get('gateway').get(gw_name)
    if 'encrypt_key' in gw_conf and 'encrypt_secret' in gw_conf:
        try:
            abpwd = os.getenv("ABPWD", "abquanT%go2moon!")
            gw_conf['key'] = encrypt(gw_conf['encrypt_key'], abpwd)
            gw_conf['secret'] = decrypt(gw_conf['encrypt_secret'], abpwd)
            gw_conf.pop('encrypt_key')
            gw_conf.pop('encrypt_secret')
        except Exception as e:
            print(f'Error occurs when decrypting key and secret for gateway {gw_name}')
            return
    else:
        print(f'Error: no (encrypted) key and secret config for gateway {gw_name}')
        return

    binance_setting = {
        "key": gw_conf['key'],
        "secret": gw_conf['secret'],
        "session_number": 3,
        # "127.0.0.1" str类型
        "proxy_host": config['proxy_host'] if 'proxy_host' in config else "",
        # 1087 int类型
        "proxy_port": config['proxy_port'] if 'proxy_port' in config else 0,
        "test_net": config['test_net'] if 'test_net' in gw_conf else 'TESTNET',
    }

    common_setting = {
        "lark_url": config.get('lark_url') if 'lark_url' in config else None,
        "log_path": config.get('log_path') if 'log_path' in config else None,
    }
    # 初始化 monitor
    monitor = Monitor(common_setting)
    monitor.start()

    event_dispatcher = EventDispatcher(interval=1)
    strategy_runner = LiveStrategyRunner(event_dispatcher)
    #设置monitor
    strategy_runner.set_monitor(monitor)

    # 注册一下 log 事件的回调函数， 该函数决定了如何打log。
    # event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
    #     "LOG--{}. {}. gateway: {}; msg: {}".format(
    #         getLevelName(event.data.level),
    #         event.data.time,
    #         event.data.gateway_name,
    #         event.data.msg)
    # ))
    # event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(str('ACCOUNT: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(str('POSITION: ') + str(event.data)))

    binance_spot_gateway = BinanceSGateway(event_dispatcher)
    binance_spot_gateway.connect(binance_setting)
    binance_ubc_gateway = BinanceUBCGateway(event_dispatcher)
    binance_ubc_gateway.connect(binance_setting)
    binance_bbc_gateway = BinanceBBCGateway(event_dispatcher)
    binance_bbc_gateway.connect(binance_setting)

    # 等待连接成功。
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
    binance_spot_gateway.set_subscribe_mode(subscribe_mode)
    binance_ubc_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)
    binance_bbc_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)

    from abquant.gateway.binancec import symbol_contract_map
    # for k, v in symbol_contract_map.items():
    #     print(v)
    ab_symbols = [generate_ab_symbol(
        symbol, exchange=Exchange.BINANCE) for symbol in symbol_contract_map.keys()]
    # this is subscribe all
    time.sleep(5)
    print("{} instrument symbol strategy0 subscribed: ".format(
        len(ab_symbols)), ab_symbols)
    # strategy 订阅所有binance合约 的金融产品行情数据。

    from abquant.gateway.binances import symbol_contract_map
    # for k, v in symbol_contract_map.items():
    #     print(v)
    strategy_runner.add_strategy(strategy_class=TheStrategy,
                                 strategy_name='the_strategy1',
                                 ab_symbols=["BTCUSDT.BINANCE",
                                             "ethusdt.BINANCE"],
                                 setting={"param1": 1, "param2": 2}
                                 )
    strategy_runner.add_strategy(strategy_class=TheStrategy,
                                 strategy_name='the_strategy2',
                                 ab_symbols=["BTCUSD_PERP.BINANCE",
                                             "ETHUSD_PERP.BINANCE"],
                                 setting={"param1": 3, "param2": 4}
                                 )
    strategy_runner.init_all_strategies()

    # 策略 start之前 sleepy一段时间， 新的策略实例有可能订阅新的产品行情，这使得abquant需要做一次与交易所的重连操作。
    time.sleep(5)
    strategy_runner.start_all_strategies()

    import random
    while True:
        time.sleep(300)
        # renew strategy1 setting.
        # edit_strategy 方法用于修改策略的 parameter。 random在这里就是一个示例。
        the_strategy1_setting = {"param1": 2,
                                 "param2": 2 * random.uniform(0, 1)}
        strategy_runner.edit_strategy(
            strategy_name='the_strategy1', setting=the_strategy1_setting)

if __name__ == '__main__':
    main()
