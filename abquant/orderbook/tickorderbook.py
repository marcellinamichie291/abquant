
from typing import overload
from .import OrderBook
from abquant.trader.msg import TickData, OrderData

class TickOrderBook(OrderBook):
    
    # TODO
    def update_bar(self, bar: TickData) -> None:
        return super().update_bar(bar)
    
    def insert_order(self, order: OrderData) -> OrderData:
        return super().insert_order(order)
