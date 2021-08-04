from abc import ABC, abstractmethod
from copy import copy
from typing import Dict, Set, List, TYPE_CHECKING
from collections import defaultdict

from abquant.trader.common import Interval, Direction, Offset
from abquant.trader.msg import BarData, TickData, OrderData, TradeData, TransactionData, EntrustData, DepthData

from .engine import StrategyEngine


class StrategyTemplate(ABC):
    """"""


    parameters = []
    variables = []

    def __init__(
        self,
        strategy_engine: StrategyEngine,
        strategy_name: str,
        ab_symbols: List[str],
        setting: dict,
    ):
        """"""
        self.strategy_engine: StrategyEngine = strategy_engine
        self.strategy_name: str = strategy_name
        self.ab_symbols: List[str] = ab_symbols

        self.inited: bool = False
        self.trading: bool = False
        self.pos: Dict[str, int] = defaultdict(int)

        self.orders: Dict[str, OrderData] = {}
        self.active_orderids: Set[str] = set()

        # Copy a new variables list here to avoid duplicate insert when multiple
        # strategy instances are created with the same strategy class.
        self.variables: List = copy(self.variables)
        self.variables.insert(0, "inited")
        self.variables.insert(1, "trading")
        self.variables.insert(2, "pos")

        self.update_setting(setting)

    def update_setting(self, setting: dict) -> None:
        """
        更新策略的超参数。
        """
        for name in self.parameters:
            if name in setting:
                setattr(self, name, setting[name])

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
            "author": self.author,
            "parameters": self.get_parameters(),
            "variables": self.get_variables(),
        }
        return strategy_data

    @abstractmethod
    def on_init(self) -> None:
        """
        策略初始化的Callback 
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
        策略正式运行的callback。 
        """
        pass

    @abstractmethod
    def on_tick(self, tick: TickData) -> None:
        """
        tickData 更新的Callback.
        """
        pass

    @abstractmethod
    def on_entrust(self, entrust: EntrustData) -> None:
        """
        委托单信息更新时的callback。通常用于重建orderbook， 尽量不要实现，而是是哟经on_tick的最优5档，因为1. 短期内回测不会支持，2.大多数交易所不提供该广播委托/交易单的功能。
        """
        pass

    def on_depth(self, depth: DepthData) -> None:
        """
        深度数据更新时的callback。通常用于重建orderbook， 尽量不要实现，而是是哟经on_tick的最优5档，因为短期内回测不会支持，
        """
        pass

    def on_transaction(self, transaction: TransactionData) -> None:
        """
        交易所成交数据更新时的callback。通常用于订单流相关的策略，尽量不要实现，而是是经由on_tick的last_trade，以及timestamp实现，因为短期内回测不会支持。
        """
        pass

    def on_depth(self, depth: DepthData) -> None:
        """
        Callback of new taker filled. Usually for collect factor of stream o
        """
        pass
 

 


    def update_trade(self, trade: TradeData) -> None:
        """
        Callback of new trade data update.
        """
        if trade.direction == Direction.LONG:
            self.pos[trade.ab_symbol] += trade.volume
        else:
            self.pos[trade.ab_symbol] -= trade.volume

    def update_order(self, order: OrderData) -> None:
        """
        Callback of new order data update.
        """
        self.orders[order.ab_orderid] = order

        if not order.is_active() and order.ab_orderid in self.active_orderids:
            self.active_orderids.remove(order.ab_orderid)

    def buy(self, ab_symbol: str, price: float, volume: float, lock: bool = False, net: bool = False) -> List[str]:
        """
        Send buy order to open a long position.
        """
        return self.send_order(ab_symbol, Direction.LONG, Offset.OPEN, price, volume, lock, net)

    def sell(self, ab_symbol: str, price: float, volume: float, lock: bool = False, net: bool = False) -> List[str]:
        """
        Send sell order to close a long position.
        """
        return self.send_order(ab_symbol, Direction.SHORT, Offset.CLOSE, price, volume, lock, net)

    def short(self, ab_symbol: str, price: float, volume: float, lock: bool = False, net: bool = False) -> List[str]:
        """
        Send short order to open as short position.
        """
        return self.send_order(ab_symbol, Direction.SHORT, Offset.OPEN, price, volume, lock, net)

    def cover(self, ab_symbol: str, price: float, volume: float, lock: bool = False, net: bool = False) -> List[str]:
        """
        Send cover order to close a short position.
        """
        return self.send_order(ab_symbol, Direction.LONG, Offset.CLOSE, price, volume, lock, net)

    def send_order(
        self,
        ab_symbol: str,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float,
        lock: bool = False,
        net: bool = False,
    ) -> List[str]:
        """
        Send a new order.
        """
        if self.trading:
            ab_orderids = self.strategy_engine.send_order(
                self, ab_symbol, direction, offset, price, volume, lock, net
            )

            for ab_orderid in ab_orderids:
                self.active_orderids.add(ab_orderid)

            return ab_orderids
        else:
            return []

    def cancel_order(self, ab_orderid: str) -> None:
        """
        Cancel an existing order.
        """
        if self.trading:
            self.strategy_engine.cancel_order(self, ab_orderid)

    def cancel_all(self) -> None:
        """
        Cancel all orders sent by strategy.
        """
        for ab_orderid in list(self.active_orderids):
            self.cancel_order(ab_orderid)

    def get_pos(self, ab_symbol: str) -> int:
        """"""
        return self.pos.get(ab_symbol, 0)

    def get_order(self, ab_orderid: str) -> OrderData:
        """"""
        return self.orders.get(ab_orderid, None)

    def get_all_active_orderids(self) -> List[OrderData]:
        """"""
        return list(self.active_orderids)

    def write_log(self, msg: str) -> None:
        """
        Write a log message.
        """
        self.strategy_engine.write_log(msg, self)

    def load_bars(self, days: int, interval: Interval = Interval.MINUTE) -> None:
        """
        Load historical bar data for initializing strategy.
        """
        self.strategy_engine.load_bars(self, days, interval)

    def put_event(self) -> None:
        """
        Put an strategy data event for ui update.
        """
        if self.inited:
            self.strategy_engine.put_strategy_event(self)

    def send_email(self, msg) -> None:
        """
        Send email to default receiver.
        """
        if self.inited:
            self.strategy_engine.send_email(msg, self)

    def sync_data(self):
        """
        Sync strategy variables value into disk storage.
        """
        if self.trading:
            self.strategy_engine.sync_strategy_data(self)
