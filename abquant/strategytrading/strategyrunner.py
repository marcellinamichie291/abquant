

from abc import ABC, abstractmethod
from logging import INFO
from typing import Iterable
from abquant.monitor import Monitor, DummyMonitor
from abquant.trader.common import Direction, Interval, Offset, OrderType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abquant.strategytrading.template import StrategyTemplate

LOG_LEVEL = int


class StrategyManager(ABC):
    @abstractmethod
    def add_strategy(
            self,
            strategy_class: type,
            strategy_name: str,
            ab_symbols: list,
            setting: dict) -> None:
        pass

    @abstractmethod
    def edit_strategy(self, strategy_name: str, setting: dict):
        pass

    @abstractmethod
    def get_strategy(self, strategy_name: str):
        pass

    @abstractmethod
    def remove_strategy(self, strategy_name: str):
        pass


class StrategyRunner(ABC):

    def __init__(self):
        self.monitor = DummyMonitor()

    def set_monitor(self, monitor: Monitor):
        self.monitor = monitor

    @abstractmethod
    def compile_check(self, strategy_class: type):
        pass

    @abstractmethod
    def load_bars(self,
                  strategy: "StrategyTemplate",
                  days: int,
                  interval: Interval = Interval.MINUTE):
        pass

    @abstractmethod
    def write_log(self, msg: str, strategy: "StrategyTemplate" = None, level: LOG_LEVEL = INFO):
        pass

    @abstractmethod
    def send_order(self,
                   strategy: "StrategyTemplate",
                   ab_symbol: str,
                   direction: Direction,
                   price: float,
                   volume: float,
                   offset: Offset,
                   order_type: OrderType) -> Iterable[str]:
        pass

    @abstractmethod
    def cancel_order(self, strategy: "StrategyTemplate", ab_orderid: str):
        pass

    @abstractmethod
    def cancel_orders(self, strategy: "StrategyTemplate", ab_orderids: Iterable[str]):
        pass

    @abstractmethod
    def notify_lark(self, strategy: "StrategyTemplate", msg: str):
        pass
