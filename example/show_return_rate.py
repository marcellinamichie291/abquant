from datetime import datetime
import threading
from typing import Dict, List
import argparse
from logging import getLevelName
import time
from pprint import pprint

from abquant.trader.tool import BarAccumulater, BarGenerator
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


class ShowStrategy(StrategyTemplate):
    window = 30
    parameters = [
        "window"
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
        self.bar_accumulator: BarAccumulater = None
        self.last_tick_time = None
        self.last_window_bars = None

    def on_init(self):
        for ab_symbol in self.ab_symbols:
            self.bgs[ab_symbol] = BarGenerator(lambda bar: None, interval=5)
        # 聚合 bars 生成 window_bars， 根据k线生成 比如window分钟k线的barData， 并且调用 on_window_bars 回调函数。
        self.bar_accumulator = BarAccumulater(
            window=self.window, on_window_bars=self.on_window_bars)

        # init时 从交易所获取过去n 天的1 分钟k线。生成 60 * 24 个供 strategy.on_bars 调用的 bars: Dict[str, BarData], 字典的key是 ab_symbol, value是BarData.
        # 从交易所获取后，顺序调用on_bars 60 * 24 次，再返回。
        # 由于是strategy实例尚未 start，因此在on_bars中调用的下单请求，不会发送，同时处理回报的update_order/trade 方法也不会被调用。
        # 即load_bars 方法适用于 需要根据历史k线预热的策略。 比如计算3日均线。使用该方法，可以避免strategy实例，上线后预热3日后正式开始交易。
        n = 5
        self.load_bars(n)
        self.write_log("策略初始化")

    def on_start(self):
        self.write_log("策略启动")

    def on_stop(self):
        self.write_log("策略停止")

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
            self.on_bars(bars)

        bg: BarGenerator = self.bgs[tick.ab_symbol]
        bg.update_tick(tick)
        if self.last_tick_time:
            self.last_tick_time = tick.datetime if tick.datetime > self.last_tick_time else self.last_tick_time
        else:
            self.last_tick_time = tick.datetime

    def on_bars(self, bars: Dict[str, BarData]):
        # 分钟级策略逻辑在这里实现， 注意策略里面不得出现任何 IO操作IO操作请使用strategyTemplate提供的接口。所有startegyTemplate提供的接口以下代码都有使用。 如 write_log, sell, buy, short, cover。
        # 更新window_bar生成器， 方便生成 n分钟k线。
        self.bar_accumulator.update_bars(bars)

    def on_window_bars(self, bars: Dict[str, BarData]):
        # window分钟级策略在这里实现， 注意设置 window参数。方便
        if self.last_window_bars is None:
            self.last_window_bars = bars
        window_returns = {}
        for ab_symbol, bar in bars.items():
            window_returns[ab_symbol] = (bar.close_price / self.last_window_bars[ab_symbol].close_price - 1) 
        self.write_log("datetime: {}, {}  minutes WINDOW,  return rate: {}".format(bar.datetime, self.window, window_returns))
        
        self.last_window_bars = bars

    

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

    def update_order(self, order: OrderData) -> None:
        # 订单状态改变发生的回调。
        super().update_order(order)


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

    # 注册一下 log 事件的回调函数， 该函数决定了如何打log。
    event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
        "LOG--{}. {}. gateway: {}; msg: {}".format(
            getLevelName(event.data.level),
            event.data.time,
            event.data.gateway_name,
            event.data.msg)
    ))
    event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(
        str('ACCOUNT: ') + str(event.data)))  # pass accessor,  trade_listerer not done
    # event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data))) # pass
    event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(
        str('POSITION: ') + str(event.data)))

    binance_ubc_gateway = BinanceUBCGateway(event_dispatcher)
    binance_ubc_gateway.connect(binance_setting)

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
    binance_ubc_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)

    strategy_runner = LiveStrategyRunner(event_dispatcher)
    from abquant.gateway.binancec import symbol_contract_map
    ab_symbols = [generate_ab_symbol(
        symbol, exchange=Exchange.BINANCE) for symbol in symbol_contract_map.keys()]
    ab_symbols_subscribed = ab_symbols[:2]
    ab_symbols_subscribed = ['BTCUSDT.BINANCE', 'ETHUSDT.BINANCE']
    # this is subscribe all
    print("{} instrument symbol strategy0 subscribed: ".format(
        len(ab_symbols_subscribed)), ab_symbols_subscribed)
    # strategy 订阅所有binance合约 的金融产品行情数据。


    strategy_runner.add_strategy(strategy_class=ShowStrategy,
                                 strategy_name='the_strategy, 60min',
                                 ab_symbols=ab_symbols_subscribed,

                                 # 60 分钟收益率
                                 setting={"window": 60 * 24}
                                 )
    strategy_runner.init_all_strategies()

    # 策略 start之前 sleepy一段时间， 新的策略实例有可能订阅新的产品行情，这使得abquant需要做一次与交易所的重连操作。
    time.sleep(5)
    strategy_runner.start_all_strategies()

    import random
    while True:
        # renew strategy1 setting.
        time.sleep(5)
        # edit_strategy 方法用于修改策略的 parameter。 random在这里就是一个示例。

    # print([c.func.id for c in ast.walk(ast.parse(inspect.getsource(TheStrategy))) if isinstance(c, ast.Call)])
if __name__ == '__main__':
    main()
    # test()
