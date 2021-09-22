from typing import List, Dict
from datetime import datetime

import numpy as np

from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.trader.tool import BarGenerator,  BarAccumulater # 后续实现， 并给出样例。
from abquant.trader.common import Direction
from abquant.trader.msg import TickData, BarData, TradeData, OrderData, EntrustData, TransactionData, DepthData


class MyStrategy(StrategyTemplate):
    """"""

    # parameter 超参数 初始化时确定，在初始化阶段被调用setattr(strategy, variable_name, variable_value)成为 object属性
    THRESHOLD = 50
    PRICE_ADD = 5
    VOLUME = 10

    # variable 可变可计算参数，在策略运行时经常更新，通常用于缓存因子,  在初始化阶段被调用setattr(strategy, variable_name, variable_value)成为 object属性
    leg1_symbol = ""
    leg2_symbol = ""
 
    parameters = [
        "THRESHOLD",
        "PRICE_ADD",
        "VOLUME"
    ]
    variables = [
        "leg1_symbol",
        "leg2_symbol",
    ]
    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        ab_symbols: List[str],
        setting: dict
    ):
        """"""
        
        super().__init__(strategy_engine, strategy_name, ab_symbols, setting)

        self.bgs: Dict[str, BarGenerator] = {}
        self.targets: Dict[str, int] = {}
        self.last_tick_time: datetime = None

        self.leg1_symbol, self.leg2_symbol = ab_symbols



    def on_init(self):
        """
        """
        self.write_log("策略初始化")

        # 既往数据缓存
        self.spread_data: np.array = np.zeros(100)

        # Obtain contract info

        def on_bar(bar: BarData):
            pass

        for ab_symbol in self.ab_symbols:
            self.bgs[ab_symbol] = BarGenerator(self.on_5s_bar, interval=5)
            self.bar_accumulator = BarAccumulater
        self.load_bars(1)



    def on_start(self):
        """
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        见父类
        """
        #  判断tick来自新一分钟
        if (
            self.last_tick_time
            and self.last_tick_time.minute != tick.datetime.minute
        ):
            bars = {}
            for ab_symbol, bg in self.bgs.items():
                bars[ab_symbol] = bg.generate()
            # 生成新的k线数据后，主动调用 on_bars。
            self.on_bars(bars)

        bg: BarGenerator = self.bgs[tick.ab_symbol]
        bg.update_tick(tick)

        self.last_tick_time = tick.datetime

    def on_bar(self, bar: BarData):
        # query
        pass


    def on_5s_bar(self, bar:BarData):
        pass
    

    def on_bars(self, bars: Dict[str, BarData]):
        """
         该回调函数 在 ontick 出现新一分钟tick数据中 使用bargenerator，生成barData数据。
        """
        # 全部撤单撤单
        self.cancel_all()

        # 存在非主力合约，一分钟无数据更新的情况，
        if self.leg1_symbol not in bars or self.leg2_symbol not in bars:
            return


        leg1_bar = bars[self.leg1_symbol]
        leg2_bar = bars[self.leg2_symbol]

        self.current_spread = (
            leg1_bar.close_price  - leg2_bar.close_price 
        )

        # 更新既往 100个 差价数据
        self.spread_data[0: -1] = self.spread_data[1:]
        self.spread_data[-1] = self.current_spread


        # 观察现有仓位。
        leg1_pos = self.get_pos(self.leg1_symbol)
        leg2_pos = self.get_pos(self.leg2_symbol)

        # 计算仓位差。
        pos_delta = abs(leg1_pos) - abs(leg2_pos)


        # 计算开仓信号， 根据目前仓位差，调整开仓量。 这里我没有细想，随意发挥吧。
        if self.current_spread > self.THRESHOLD:
            if pos_delta > 0:
                self.sell(leg1_bar.ab_symbol, leg1_bar.close_price + self.PRICE_ADD, self.VOLUME + abs(pos_delta))
                self.buy(leg2_bar.ab_symbol[1], leg2_bar.close_price - self.PRICE_ADD, self.VOLUME )
            else:
                self.sell(leg1_bar.ab_symbol, leg1_bar.close_price + self.PRICE_ADD, self.VOLUME )
                self.buy(leg2_bar.ab_symbol[1], leg2_bar.close_price - self.PRICE_ADD, self.VOLUME + abs(pos_delta) )
 
        elif  self.current_spread < - self.THRESHOLD:  
            self.buy(leg1_bar.ab_symbol, leg1_bar.close_price + self.PRICE_ADD, self.VOLUME + pos_delta)
            self.sell(leg2_bar.ab_symbol, leg2_bar.close_price - self.PRICE_ADD, self.VOLUME)

    def on_entrust(self, entrust: EntrustData) -> None:
        """
        较长一段时间内不建议使用
        见父类
        """
        pass

    def on_transaction(self, transaction: TransactionData) -> None:
        """
        暂时不建议使用
        见父类
        """
        pass

    def on_depth(self, depth: DepthData) -> None:
        """
        暂时不建议使用
        见父类
        """
        pass
    
    def on_exception(self, transaction: Exception) -> None:
        """
        见父类
        """
        pass

    def update_trade(self, trade: TradeData) -> None:
        """
        见父类
        """
        super(MyStrategy, self).update_trade(trade)
        self.write_log("pos update: {}, {}".format(trade.symbol, self.pos[trade.symbol]))

    def update_order(self, order: OrderData) -> None:
        """
        见父类
        """
        super(MyStrategy, self).update_order(order)
        self.write_log("order still active: {}".format(self.active_orderids))
        self.write_log("order {} status: {}".format(order.ab_orderid, order.status))

if __name__ == '__main__':
    pass
