


from typing import Dict, List
import numpy as np
import talib

from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.trader.tool import ArrayCache, BarGenerator,  BarAccumulater 
from abquant.trader.common import Direction, OrderType, Status
from abquant.trader.msg import TickData, BarData, TradeData, OrderData, EntrustData, TransactionData, DepthData





class DoubleMAStrategy(StrategyTemplate):
    # 一下类属性/成员， 均由交易员自行决定并声明。

    short_window = 3
    long_window = 10
    U_per_trade = 100


    # 声明可配置参数，本行之上是可配置参数的默认值。
    parameters = [
        "short_window",
        "long_window",
        "U_per_trade"
    ]
    # 声明未来可能出现的，可能需盘中纪录的可计算参数， 如需监控的因子值，以及各金融产品的仓位变化等等， 后续提供支持。
    variables = [
        "last_short_ma",
        "short_ma",
        "last_long_ma",
        "long_ma",
        "cross_over",
        "cross_below",
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
            self.bgs[ab_symbol] = BarGenerator(lambda bar: None, interval=1)
        self.array_cache = ArrayCache(self.long_window * 2)

        # init时 从交易所获取过去n 天的1 分钟k线。生成 60 * 24 个供 strategy.on_bars 调用的 bars: Dict[str, BarData], 字典的key是 ab_symbol, value是BarData.
        # 从交易所获取后，顺序调用on_bars 60 * 24 次，再返回。
        # 由于是strategy实例尚未 start，因此在on_bars中调用的下单请求，不会发送，同时处理回报的update_order/trade 方法也不会被调用。
        # 即load_bars 方法适用于 需要根据历史k线预热的策略。 比如计算3日均线。使用该方法，可以避免strategy实例，上线后预热3日后正式开始交易。
        n_days = int(self.long_window / (24 * 60)) + 1
        self.write_log("replay the last {} days.".format(n_days))
        self.load_bars(n_days)
        self.write_log("replay done.")
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
            if all(bars.values()):
                self.on_bars(bars)


        bg: BarGenerator = self.bgs[tick.ab_symbol]
        bg.update_tick(tick)
        if self.last_tick_time:
            self.last_tick_time = tick.datetime if tick.datetime > self.last_tick_time else self.last_tick_time
        else:
            self.last_tick_time = tick.datetime

    def on_bars(self, bars: Dict[str, BarData]):
        ab_symbol = self.ab_symbols[0]
        self.array_cache.update_bar(bars[ab_symbol])
        close_price = bars[ab_symbol].close_price
        if not self.array_cache.inited:
            return

        self.cancel_all()
        
        short_ma = talib.SMA(self.array_cache.close, self.short_window)
        self.last_short_ma = short_ma[-2]
        self.short_ma = short_ma[-1]
        
        long_ma = talib.SMA(self.array_cache.close, self.long_window)
        self.last_long_ma = long_ma[-2]
        self.long_ma = long_ma[-1]

        cross_over = self.short_ma > self.long_ma and self.short_ma < self.last_long_ma
        cross_below = self.short_ma < self.long_ma and self.short_ma > self.last_long_ma
        self.write_log("short_ma:{}, long_ma:{}, cross_over:{}, cross_below:{}".format(self.short_ma, self.long_ma, cross_over, cross_below))
        

        # volume_per_trade = self.U_per_trade / close_price
        volume_per_trade = self.U_per_trade 
        position = self.get_pos(ab_symbol)
        self.write_log("position: {}".format(position))
        if cross_over:
            if  position == 0:
                self.buy(ab_symbol, close_price, volume_per_trade, OrderType.LIMIT)
            elif position < 0:
                self.cover(ab_symbol, close_price, abs(position), OrderType.MARKET)
                self.buy(close_price, close_price, volume_per_trade, OrderType.LIMIT)

        elif cross_below:
            if position == 0:
                self.short(ab_symbol, close_price, volume_per_trade, OrderType.LIMIT)
            elif position > 0:
                self.sell(ab_symbol, close_price, abs(position), OrderType.MARKET)
                self.short(ab_symbol, close_price, volume_per_trade, OrderType.LIMIT)
        # self.sync_data()


    def on_window_bars(self, bars: Dict[str, BarData]):
        # window分钟级策略在这里实现， 注意设置 window参数。方便
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
        # self.write_log("pos update: {} filled with {}. #trade details: {}".format(
        #     trade.ab_symbol, self.pos[trade.ab_symbol], trade))

    def update_order(self, order: OrderData) -> None:
        # 订单状态改变发生的回调。
        super().update_order(order)
        self.write_log("update order: {}".format(order))
        if order.status == Status.SUBMITTING:
            self.write_log("update order: {}".format(order))
        elif order.status == Status.ALLTRADED:
            self.write_log("update order: {}".format(order))
        elif order.status == Status.CANCELLED :
            self.write_log("update order: {}".format(order))
        elif order.status == Status.REJECTED:
            self.write_log("update order: {}".format(order))
           