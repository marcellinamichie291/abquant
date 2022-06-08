from abc import ABC, abstractmethod
from itertools import chain
from typing import Any, Dict, Iterable, Optional, Tuple
from abquant.trader.common import OrderType, Status
from abquant.trader.msg import DepthData, BarData, EntrustData, OrderData, TickData, TradeData

class OrderBook(ABC):
    SUPPORTED_ORDERTYPE = {OrderType.LIMIT, OrderType.STOP_MARKET}
    def __init__(self):
        self.active_limit_orders: Dict[str, OrderData] = {}
        self.stop_market_orders: Dict[str, OrderData] = {}

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
        if order.type not in self.SUPPORTED_ORDERTYPE:
            raise ValueError("{} order rerceived. order type other than {} are not going to support.".format(order.type, self.SUPPORTED_ORDERTYPE))
        if order.type == OrderType.LIMIT:
            self.active_limit_orders[order.ab_orderid] = order
        elif order.type == OrderType.STOP_MARKET:
            self.stop_market_orders[order.ab_orderid] = order
        return order.ab_orderid

    @abstractmethod
    def cancel_order(self, ab_orderid: str) -> Optional[OrderData]:
        self.pre_matching()
        if ab_orderid in self.active_limit_orders:
            order = self.active_limit_orders.pop(ab_orderid)
        elif ab_orderid in self.stop_market_orders:
            order = self.stop_market_orders.pop(ab_orderid)
        else:
            return None
        order.status = Status.CANCELLED
        return order
    
    @abstractmethod
    def match_orders(self) -> Iterable[Tuple[OrderData, TradeData]]:
        self.pre_matching()
        pass

    def submitting_orders(self) -> Iterable[OrderData]:
        self.pre_matching()
        return (order for order in chain(self.active_limit_orders.values(), self.stop_market_orders.values()) if order.status == Status.SUBMITTING)
    
    def accept_submitting_orders(self) -> Iterable[OrderData]:
        self.pre_matching()
        for order in self.submitting_orders():
            order.status = Status.NOTTRADED
            yield order
    
    def pre_matching(self):
        pass
    