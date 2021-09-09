from abc import ABC, abstractmethod
from typing import Any
from abquant.trader.msg import DepthData, BarData, EntrustData, OrderData, TickData

class OrderBook(ABC):
    def __init__(self):
        pass

    @staticmethod
    def orderbook_factory(mode: str) -> "OrderBook":
        if mode == 'Bar':
            pass
        elif mode == 'Tick':
            pass
        else:
            raise ValueError("order bokk other than tick level or bar level are not going to support.")

    @abstractmethod
    def update_depth(self, depth: DepthData) -> None:
        pass
    
    @abstractmethod
    def update_bar(self, bar: BarData) -> None:
        pass

    @abstractmethod
    def update_entrust(self, entrust: EntrustData) -> None:
        pass

    @abstractmethod
    def update_tick(self, tick: TickData) -> None:
        pass

    # type not specified
    @abstractmethod
    def insert_order(self, order: OrderData) -> OrderData:
        pass
