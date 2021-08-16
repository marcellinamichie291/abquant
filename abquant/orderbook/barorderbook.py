from typing import overload
from .import OrderBook
from abquant.trader.msg import BarData, TickData
from abquant.trader.object import OrderData

class BarOrderBook(OrderBook):
    
    # TODO
    def update_bar(self, bar: BarData) -> None:
        return super().update_bar(bar)
    
    def insert_order(self, order: OrderData) -> OrderData:
        return super().insert_order(order)
