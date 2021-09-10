

from abquant.trader.common import Interval
from abquant.trader.msg import BarData, TickData, TransactionData
from typing import Callable, Optional


class BarGenerator:
    def __init__(self, interval):
        pass

class BarGenerator:
    """
    For:
    1. generating 1 minute bar data from tick data
    2. generateing x minute bar/x hour bar data from 1 minute data

    Notice:
    1. for x minute bar, x must be able to divide 60: 2, 3, 5, 6, 10, 15, 20, 30
    2. for x hour bar, x can be any number
    """

    def __init__(
        self,
        on_bar: Callable,
        window: int = 0,
        on_window_bar: Callable = None,
        interval: Interval = Interval.MINUTE
    ):
        self.bar: BarData = None
        self.on_bar: Callable = on_bar

        self.interval: Interval = interval
        self.interval_count: int = 0

        self.hour_bar: BarData = None

        self.window: int = window
        self.window_bar: BarData = None
        self.on_window_bar: Callable = on_window_bar

        self.last_tick: TickData = None
        self.last_bar: BarData = None

        self.last_transaction: TransactionData = None


    def update_tick(self, tick: TickData) -> None:
        """
        either update_tick or update_transaction. use both at same time is not allowed. 
        """
        pass

    def update_transaction(self, tick: TransactionData) -> None:
        pass

    def update_bar(self, bar: BarData) -> None:
        pass

    def update_bar_minute_window(self, bar: BarData) -> None:
        pass

    def update_bar_hour_window(self, bar: BarData) -> None:
        pass

    def on_hour_bar(self, bar: BarData) -> None:
        pass

    def generate(self) -> Optional[BarData]:
        pass

class ArrayCache:
    def __init__(self, size: int):
        pass