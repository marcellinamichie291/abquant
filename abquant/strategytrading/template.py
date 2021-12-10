from abc import ABC, abstractmethod
import time
from logging import INFO
from abquant import gateway
from abquant.event.dispatcher import Event
from copy import copy
from typing import Dict, Set, List, TYPE_CHECKING
from collections import defaultdict

from abquant.trader.common import Interval, Direction, Offset, OrderType
from abquant.trader.msg import BarData, TickData, OrderData, TradeData, TransactionData, EntrustData, DepthData
from abquant.trader.object import LogData

# TODO typechecking  and same thing in msg.py

from .strategyrunner import StrategyRunner

class StrategyTemplate(ABC):
    """"""

    parameters = []
    variables = []

    def __init__(
        self,
        strategy_runner: StrategyRunner,
        strategy_name: str,
        ab_symbols: List[str],
        setting: dict,
    ):
        """"""
        self.strategy_runner = strategy_runner
        self.strategy_name: str = strategy_name
        self.ab_symbols: List[str] = ab_symbols

        self.run_id = "{}-{}".format(strategy_name, int(time.time()))

        self.inited: bool = False
        self.trading: bool = False
        self.pos: Dict[str, float] = defaultdict(float)

        self.orders: Dict[str, OrderData] = {}
        self.active_orderids: Set[str] = set()

        # Copy a new variables list here to avoid duplicate insert when multiple
        # strategy instances are created with the same strategy class.
        self.variables: List = copy(self.variables)

        self.update_setting(setting)

    def update_setting(self, setting: dict) -> None:
        """
        更新策略的超参数。
        """
        for name in self.parameters:
            if name in setting:
                setattr(self, name, setting[name])
        self.strategy_runner.monitor.send_parameter(self.run_id, self.get_parameters())

    @classmethod
    def get_class_parameters(cls) -> Dict:
        """
        get 策略声明的超参数的默认值
        """
        class_parameters = {}
        for name in cls.parameters:
            class_parameters[name] = getattr(cls, name)
        return class_parameters

    def get_parameters(self) -> Dict:
        """
        get 策略实例声明的超参数的值
        """
        strategy_parameters = {}
        for name in self.parameters:
            strategy_parameters[name] = getattr(self, name)
        return strategy_parameters

    def get_variables(self) -> Dict:
        """
        get 策略实例声明的可变参数的值。
        """
        strategy_variables = {}
        for name in self.variables:
            strategy_variables[name] = getattr(self, name)
        return strategy_variables

    def get_data(self) -> Dict:
        """
        get 策略的元信息。
        """
        strategy_data = {
            "strategy_name": self.strategy_name,
            "ab_symbols": self.ab_symbols,
            "class_name": self.__class__.__name__,
            "parameters": self.get_parameters(),
            "variables": self.get_variables(),
        }
        return strategy_data

    @abstractmethod
    def on_init(self) -> None:
        """
        策略初始化的Callback 
        如果需要历史数据做 策略预热，那么在此处调用self.load_bars(n)
        """
        pass

    @abstractmethod
    def on_start(self) -> None:
        """
        策略正式运行的callback
        """
        pass

    @abstractmethod
    def on_stop(self) -> None:
        """
        策略正式停运的callback。 
        """
        pass

    @abstractmethod
    def on_tick(self, tick: TickData) -> None:
        """
        tickData 更新的Callback.
        """
        pass

    @abstractmethod
    def on_bars(self, bars: Dict[str, BarData]) -> None:
        """
        该方法比较特殊，在实盘中需通过BarGenerator，在on_tick中更新并回调。 
        在回测中，tick级别回测同理， 分钟bar级别回测则会被回测引擎自动调用。

        如果在on_init中调用了 self.load_bars(n). 那么该方法会在回放过去n天的分钟bar数据中被不断调用， 
        共计安时序调用 n * 24 * 60 次。
        此时的策略实例并不在trading状态，因此并未开始交易，而是在做策略的计算预热。
        """
        pass

    def on_entrust(self, entrust: EntrustData) -> None:
        """
        委托单信息更新时的callback。通常用于重建orderbook.
        尽量不要实现，而是是经on_tick的最优5档，
        因为1. 短期内回测不会支持，2.大多数交易所不提供该广播委托/交易单的功能。
        """
        pass

    def on_depth(self, depth: DepthData) -> None:
        """
        深度数据更新时的callback。通常用于重建orderbook.
        尽量不要实现，而是是哟经on_tick的最优5档，因为短期内回测不会支持。
        """
        pass

    def on_transaction(self, transaction: TransactionData) -> None:
        """
        交易所成交数据更新时的callback。通常用于订单流相关的策略.
        尽量不要实现，而是是经由on_tick， tickData中的trade_volume trade_price，以及timestamp实现，因为短期内回测不会支持。
        """
        pass

    @abstractmethod
    def on_exception(self, exception: Exception) -> None:
        """
        TODO 初步的规划是提供两个交易所可能出现的异常类， OrderException， 以及MarketException，CongestionException.
        分别对应行情订阅异常，以及订单发送异常。
        """
        pass

    def on_timer(self, interval: int) -> None:
        """
        根据 event dispatcher的 interval 决定， 默认1秒调用一次。
        Event的  data 属性是 int， 代表event dispatcher的 interval。
        """
        pass

    @abstractmethod
    def update_trade(self, trade: TradeData) -> None:
        """
        个人交易单出现成交时的callback，默认的实现是用来管理该测略相关仓位。
        重写该方法时最好 super().update_trade(trade)，调用父类StrategeTemplate该方法的实现。
        回测时会支持模拟回报，调用该方法。
        """
        self.strategy_runner.monitor.send_trade(self.run_id, trade)
        if trade.direction == Direction.LONG:
            self.pos[trade.ab_symbol] += trade.volume
        else:
            self.pos[trade.ab_symbol] -= trade.volume
        self.strategy_runner.monitor.send_position(self.run_id, trade.ab_symbol, self.pos.get(trade.ab_symbol))

    @abstractmethod
    def update_order(self, order: OrderData) -> None:
        """
        个人交易单出现成交时的callback，默认的实现是用来管理该策略的相关交易单单状态，尤其是尚处于活跃状态（可被动成交）的交易单。
        重写该方法时最好 super().update_order(order)，调用父类StrategeTemplate该方法的实现。
        回测时会支持模拟回报，调用该方法。
        """
        self.orders[order.ab_orderid] = order
        self.strategy_runner.monitor.send_order(self.run_id, order)

        if not order.is_active() and order.ab_orderid in self.active_orderids:
            self.active_orderids.remove(order.ab_orderid)
            self.orders.pop(order.ab_orderid)


    def buy(self, ab_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.MARKET) -> List[str]:
        """
        开多。
        注意事项：
        1. 有些交易所不存在Offset的概念。全部使用Offset.Open可行（如bitmex），但建议策略师依旧能够使用offset， 一方面，订单撮合存在时差，在高频做市策略里这是很有必要的保证空仓的机制，二来，回测时不会累计垃圾订单。
        2. 买卖会自动处理price tick的问题（最小可变价格），但依旧建议策略师编写师都做好价格round。尤其是做市类策略。

        """
        return self.send_order(ab_symbol, Direction.LONG, price, volume, Offset.OPEN, order_type)

    def sell(self, ab_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.MARKET) -> List[str]:
        """
        平多
        """
        return self.send_order(ab_symbol, Direction.SHORT, price, volume, Offset.CLOSE, order_type)

    def short(self, ab_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.MARKET) -> List[str]:
        """
        开空
        """
        return self.send_order(ab_symbol, Direction.SHORT, price, volume,  Offset.OPEN, order_type)

    def cover(self, ab_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.MARKET) -> List[str]:
        """
        平空 
        """
        return self.send_order(ab_symbol, Direction.LONG, price, volume, Offset.CLOSE, order_type)

    def send_order(
        self,
        ab_symbol: str,
        direction: Direction,
        price: float,
        volume: float,
        offset: Offset = Offset.OPEN,
        order_type: OrderType = OrderType.MARKET
    ) -> List[str]:
        """
        下单， 
        注意，发单操作是一个异步操作，该方法调用后 update_order方法 会立刻被回调
        orderData中status 被置为 Submitting，
        若交易单被交易所接受确认， 一段时间差后， update_order被回调，
        orderData中status 被置为 NotTraded ， Traded或 partedTraded。
        请以update_order方法被为准，从而 确定下单成功。
        TODO：批挂，在同交易所的套利，以及做市策略中有必要支持，目前没想清楚如何设计接口能同时支持回测+实盘，因此暂时将返回值设计为列表类型。
        TODO： 暂时不确定订单交易所未回报应该怎么处理。 可能会在update_order方法 被回调时，给出Rejected, 或增加Timeout的order status

        """
        if self.trading:
            ab_orderids = self.strategy_runner.send_order(
                self, ab_symbol, direction, price, volume, offset, order_type
            )

            for ab_orderid in ab_orderids:
                self.active_orderids.add(ab_orderid)

            return ab_orderids
        else:
            return []

    def cancel_order(self, ab_orderid: str) -> None:
        """
        撤单， 注意，撤单操作是一个异步操作，从该方法调用到 update_order方法 被回调
        orderData中status 被置为 Cancelled， 存在时间差。
        请以update_order方法被回调为准，确定撤单成功。若撤单失败则 order status 为Rejected。
        TODO： 暂时不确定撤单交易所未回报应该怎么处理。 可能会在update_order方法 被回调时，给出Rejected, 或增加Timeout的order statui。
        不过通常来说，交易所给cancel_order的级别极高，哪怕账户被权限冻结，一般都会保留撤单权限。

        """
        if self.trading:
            self.strategy_runner.cancel_order(self, ab_orderid)

    def cancel_orders(self, ab_orderids: List[str]) -> None:
        """
        批撤单， 注意，
        1. 不是所有交易所支持批撤操作。若不支持，则迭代调用单笔撤单操作，操作可能计入request liimt。
        2. 批撤与 cancelk_order一样，需要update_order被回调时确定调用，但由于批撤不一定能够全部成功，
        通常交易所只，尽可能撤更多的单， 因此updete_order是分别针对批单中的每一个分别回调。

        """
        if self.trading:
            self.strategy_runner.cancel_orders(self, ab_orderids)

    def cancel_all(self) -> None:
        """
        撤销该策略所有订单。
        可以考虑在on_exception时调用。
        之后可以考虑根据sync_date函数 持久化的仓位信息。去交易所手动平仓。
        """
        # for ab_orderid in list(self.active_orderids):
        #     self.cancel_order(ab_orderid)
        self.cancel_orders(list(self.active_orderids))

    def get_pos(self, ab_symbol: str) -> int:
        """"""
        return self.pos.get(ab_symbol, 0)

    def get_order(self, ab_orderid: str) -> OrderData:
        """"""
        return self.orders.get(ab_orderid, None)

    def get_all_active_orderids(self) -> List[OrderData]:
        """"""
        return list(self.active_orderids)

    def write_log(self, msg: str, level=INFO) -> None:
        """
        """
        self.strategy_runner.write_log(msg, self, level)

    def load_bars(self, days: int, interval: Interval = Interval.MINUTE) -> None:
        """
        加载过去一段时间的k线数据，通常回测，实盘皆可支持1分钟级，但存在部分交易所仅提供既往数天的分钟线。
        """
        self.strategy_runner.load_bars(self, days, interval)

    def notify_lark(self, msg: str):
        self.strategy_runner.notify_lark(self, msg)
        
    def sync_data(self):
        """
        同步 策略内相关变量。通常用于记录仓位及参数信息，以便监控及复原。
        如果调用建议发生在update_trade时进行。 因为该回调会在仓位发生变更时发生。
        """
        raise NotImplementedError("do not use for now.")
        if self.trading:
            self.strategy_runner.sync_strategy_data(self)
