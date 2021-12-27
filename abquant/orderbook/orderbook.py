from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional, Tuple
from abquant.trader.common import Status
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
        if order.status != Status.SUBMITTING:
            raise ValueError("order status must be submitting.")
        self.active_limit_orders[order.ab_orderid] = order
        return order.ab_orderid

    @abstractmethod
    def cancel_order(self, ab_orderid: str) -> Optional[OrderData]:
        if ab_orderid not in self.active_limit_orders:
            return None
        order = self.active_limit_orders.pop(ab_orderid)
        order.status = Status.CANCELLED
        return order
    
    @abstractmethod
    def match_orders(self) -> Iterable[Tuple[OrderData, TradeData]]:
        pass

    def submitting_orders(self) -> Iterable[OrderData]:
        return (order for order in self.active_limit_orders.values() if order.status == Status.SUBMITTING)
    
    def accept_submitting_orders(self) -> Iterable[OrderData]:
        for order in self.submitting_orders():
            order.status = Status.NOTTRADED
            yield order
    