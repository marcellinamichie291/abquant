from typing import Dict, List
import argparse
import time

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

    parameters = [
        "param1",
        "param2",
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

    def on_init(self):
        self.write_log("策略初始化")

    def on_start(self):
        self.write_log("策略启动")

    def on_stop(self):
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        pass

    def on_bars(self, bars: Dict[str, BarData]):
        pass

    def on_entrust(self, entrust: EntrustData) -> None:
        pass

    def on_transaction(self, transaction: TransactionData) -> None:
        pass

    def on_depth(self, depth: DepthData) -> None:
        pass

    def on_exception(self, transaction: Exception) -> None:
        pass

    def on_timer(self, ticker: Event) -> None:
        # 根据 event dispatcher的 interval 决定， 默认1秒调用一次。
        pass

    def update_trade(self, trade: TradeData) -> None:
        super().update_trade(trade)
        self.write_log("pos update: {}, {}".format(
            trade.symbol, self.pos[trade.symbol]))

    def update_order(self, order: OrderData) -> None:
        super().update_order(order)
        self.write_log("order still active: {}".format(self.active_orderids))
        self.write_log("order {} status: {}".format(
            order.ab_orderid, order.status))


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
    binance_ubc_gateway = BinanceUBCGateway(event_dispatcher)
    binance_ubc_gateway.connect(binance_setting)
    binance_bbc_gateway = BinanceBBCGateway(event_dispatcher)
    binance_bbc_gateway.connect(binance_setting)
    subscribe_mode = SubscribeMode(
        # 订阅 深度数据 depth. 除非重建orderbook，否则不开也罢。
        depth=False,
        # 订阅最优五档tick
        tick_5=True,
        # 订阅best bid/ask tick
        best_tick=True,
        # 订阅委托单（通常不支持） entrust
        entrust=False,
        # 订阅交易数据 transaction, 自动生成 tick.
        transaction=True
    )

    # 有默认值，默认全订阅, 可以不调用下面两行。
    binance_ubc_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)
    binance_bbc_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)

    strategy_runner = LiveStrategyRunner(event_dispatcher)
    strategy_runner.add_strategy(strategy_class=TheStrategy,
                                 strategy_name='the_strategy2',
                                 ab_symbols=["BTCUSDT.BINANCEUBC",
                                             "ETHUSDT.BINANCEUBC"],
                                 setting={"param1": 1, "param2": 2}
                                 )
    strategy_runner.add_strategy(strategy_class=TheStrategy,
                                 strategy_name='the_strategy2',
                                 ab_symbols=["BTCUSD_PERP.BINANCEBBC",
                                             "ETHUSD_PERP.BINANCEBBC"],
                                 setting={"param1": 3, "param2": 4}
                                 )
    strategy_runner.init_all_strategies()
    strategy_runner.start_all_strategies()


    import random
    while True:
        # renew strategy1 setting.
        time.sleep(5)
        the_strategy1_setting = {"param1": 2, "param2": 2 * random.uniform()}
        strategy_runner.edit_strategy(
            strategy_name='the_strategy1', setting=the_strategy1_setting)
        # renew strategy2 setting.
        the_strategy2_setting = {"param1": 4, "param2": 4 * random.uniform()}
        strategy_runner.edit_strategy(
            strategy_name='the_strategy2', setting=the_strategy2_setting)

if __name__ == '__main__':
    main()
