from typing import Callable, Dict, Optional, Type, Union

from abquant.trader.common import Interval
from abquant.trader.msg import BarData, TickData, TransactionData


class BarAccumulater:
    def __init__(self, window: int, on_window_bars: Callable[[Dict[str, BarData]], None]):
        self.window = window
        self.on_window = on_window_bars
        self.bars: Dict[str, BarData]= {}

        self._update_times = 0
    
    @staticmethod
    def check_datatime(bars: Dict[str, BarData]):
        bar_time = None
        for ab_symbol, bar in bars.items():
            if bar_time is None:
                bar_time = bar.datetime
            assert(bar_time == bar.datetime, "the BarData in bars has different timestamp.")
            bar_time = bar.datetime


    def update_bars(self, bars: Dict[str, BarData]):
        """
        not thread-safe
        
        """
        self.check_datatime(bars)
        self._update_times += 1
        for ab_symbol, bar in bars.items():
            if ab_symbol not in self.bars:
                self.bars[ab_symbol] = bar
            else:
                accumulated_bar = self.bars[ab_symbol]
                accumulated_bar.close_price = bar.close_price
                accumulated_bar.high_price = max(bar.high_price, accumulated_bar.high_price)
                accumulated_bar.low_price = min(bar.low_price, accumulated_bar.low_price)
                accumulated_bar.volume += bar.volume
    
        if self._update_times >= self.window:
            self.on_window(self.bars)
            self.bars = {}
            self._update_times = 0
        

class BarGenerator:
    """
    For:
    1. generating 1 minute bar data from tick data
    2. generateing x minute bar/ bar data from 1 minute data NOT SUPPORT YET.

    Notice:
    1. for x minute bar, x must be able to divide 60: 2, 3, 5, 6, 10, 15, 20, 30
    2. for x hour bar, x can be any number
    """

    def __init__(
        self,
        on_bar: Callable[[BarData], None],
        window: int = 0,
        on_window_bar: Callable = None,
        interval: Interval = Interval.MINUTE
    ):
        self.bar: BarData = None
        self.on_bar: Callable = on_bar

        self.interval: Interval = interval
        self.interval_count: int = 0

        self.window: int = window
        self.window_bar: BarData = None
        self.on_window_bar: Callable = on_window_bar

        self.last_tick: TickData = None
        self.last_bar: BarData = None
        self.last_transaction: TransactionData = None

    def update(self, data: Union[TickData, TransactionData]):
        if isinstance(data, TickData):
            self.update_tick(data)
        elif isinstance(data, TransactionData):
            self.update_transaction(data)
        else:
            raise TypeError(
                "type of data is {}, neither TickData nor Transaction.".format(type(data)))

    def update_tick(self, tick: TickData) -> None:
        """
        either update_tick or update_transaction. use both at same time is not allowed. 
        """
        if self.last_transaction:
            raise TypeError(
                "BarGenerator should be updated by either TickData or Transaction to generate BarData, updated by both of them at the same time is not allowed.")
        new_minute = False

        # Filter tick data with 0 last price
        if not tick.trade_price:
            return

        # Filter tick data with older timestamp
        if self.last_tick and tick.datetime < self.last_tick.datetime:
            return

        if not self.bar:
            new_minute = True
        elif (
            (self.bar.datetime.minute != tick.datetime.minute)
            or (self.bar.datetime.hour != tick.datetime.hour)
        ):
            self.bar.datetime = self.bar.datetime.replace(
                second=0, microsecond=0
            )
            self.on_bar(self.bar)

            new_minute = True

        if new_minute:
            self.bar = BarData(
                symbol=tick.symbol,
                exchange=tick.exchange,
                interval=Interval.MINUTE,
                datetime=tick.datetime,
                gateway_name=tick.gateway_name,
                open_price=tick.trade_price,
                high_price=tick.trade_price,
                low_price=tick.trade_price,
                close_price=tick.trade_price,
            )
        else:
            self.bar.high_price = max(self.bar.high_price, tick.trade_price)
            self.bar.low_price = min(self.bar.low_price, tick.trade_price)
            self.bar.close_price = tick.trade_price
            self.bar.datetime = tick.datetime

        if self.last_tick:
            # volume_change = tick.volume - self.last_tick.volume
            self.bar.volume += tick.trade_volume

        self.last_tick = tick

    def update_transaction(self, tick: TransactionData) -> None:
        if self.last_tick:
            raise TypeError(
                "BarGenerator should be updated by either TickData or Transaction to generate BarData, updated by both of them at the same time is not allowed.")
        pass

    def update_bar(self, bar: BarData) -> None:
        pass

    def generate(self) -> Optional[BarData]:
        """
        Generate the bar data and call callback immediately.
        """
        bar = self.bar

        if self.bar:
            bar.datetime = bar.datetime.replace(second=0, microsecond=0)
            self.on_bar(bar)
        self.bar = None
        # TODO None may not a proper choice. but every time call generate, self.bar.datetime.minut += 1 look ambigious.
        return bar


class ArrayCache:
    def __init__(self, size: int):
        pass
