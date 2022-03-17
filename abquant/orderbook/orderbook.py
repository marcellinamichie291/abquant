from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional, Tuple
from abquant.trader.common import OrderType, Status
from abquant.trader.msg import DepthData, BarData, EntrustData, OrderData, TickData, TradeData

class OrderBook(ABC):
    def __init__(self):
        self.active_limit_orders: Dict[str, OrderData] = {}

    @staticmethod
    def orderbook_factory(mode: str) -> "OrderBook":
        if mode == 'Bar':
            from .barorderbook import BarOrderBook
            return BarOrderBook()
        elif mode == 'Tick':
            pass
        else:
            raise ValueError("order bokk other than tick level or bar level are not going to support.")

    # type not specified
    @abstractmethod
    def insert_order(self, order: OrderData) -> str:
        self.pre_matching()
        assert(order.status == Status.SUBMITTING)
        if order.type != OrderType.LIMIT:
            raise ValueError("order type other than limit are not going to support.")
        self.active_limit_orders[order.ab_orderid] = order
        return order.ab_orderid

    @abstractmethod
    def cancel_order(self, ab_orderid: str) -> Optional[OrderData]:
        self.pre_matching()
        if ab_orderid not in self.active_limit_orders:
            return None
        order = self.active_limit_orders.pop(ab_orderid)
        order.status = Status.CANCELLED
        return order
    
    @abstractmethod
    def match_orders(self) -> Iterable[Tuple[OrderData, TradeData]]:
        self.pre_matching()
        pass

    def submitting_orders(self) -> Iterable[OrderData]:
        self.pre_matching()
        return (order for order in self.active_limit_orders.values() if order.status == Status.SUBMITTING)
    
    def accept_submitting_orders(self) -> Iterable[OrderData]:
        self.pre_matching()
        for order in self.submitting_orders():
            order.status = Status.NOTTRADED
            yield order
    
    def pre_matching(self):
        pass
    