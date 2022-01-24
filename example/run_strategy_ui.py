import pathlib
from typing import Dict, List

from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.trader.common import OrderType
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import SubscribeMode
from abquant.trader.tool import BarAccumulater, BarGenerator
from abquant.trader.utility import round_up
from abquantui.ab_ui_starter import ab_ui_starter
from abquantui.strategy_lifecycle import StrategyLifecycle


# 策略的实现，所有细节都需要明确。务必先看完.
class TheStrategy(StrategyTemplate):
    # 一下类属性/成员， 均由交易员自行决定并声明。
    param1 = None
    param2 = None
    trade_flag = False
    check_pos_interval = 20
    balance = 10000
    window = 3

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

class MyLifecycle(StrategyLifecycle):
    def __init__(self, config: Dict):
        super().__init__(config)

    def add_init_strategy(self):
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

        self.gateways['BINANCEUBC'].set_subscribe_mode(subscribe_mode=subscribe_mode)

        self._strategy_runner.add_strategy(strategy_class=TheStrategy,
                                     strategy_name='the_strategy1',
                                     ab_symbols=["BTCUSDT.BINANCE",
                                                 "ETHUSDT.BINANCE"],
                                     setting={"param1": 1, "param2": 2}
                                     )
        self._strategy_runner.add_strategy(strategy_class=TheStrategy,
                                     strategy_name='the_strategy2',
                                     ab_symbols=["BTCUSD_PERP.BINANCE",
                                                 "ETHUSD_PERP.BINANCE"],
                                     setting={"param1": 3, "param2": 4}
                                     )

        self._strategy_runner.init_all_strategies()


def main():
    parent_path = pathlib.Path(__file__).parent
    config_path = parent_path.joinpath('run_strategy.yaml')
    ab_ui_starter(config_path, MyLifecycle)

if __name__ == '__main__':
    main()
