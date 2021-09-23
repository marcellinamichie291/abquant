from typing import Iterable
from abquant.trader.common import Direction, Interval, Offset, OrderType
from abquant.strategytrading.template import StrategyTemplate
from .strategyrunner import StrategyRunner


class BacktestStrategyRunner(StrategyRunner):

    def __init__(self) -> None:
        pass

    def add_strategy(self, strategy_class: type, strategy_name: str, ab_symbols: list, setting: dict) -> None:
        pass

    def remove_strategy(self, strategy_name: str):
        pass

    def get_strategy(self, strategy_name: str):
        pass

    def edit_strategy(self, strategy_name: str, setting: dict):
        pass

    def compile_check(self, strategy_class: type):
        pass

    def load_bars(self, strategy: StrategyTemplate, days: int, interval: Interval = ...):
        pass

    def write_log(self, msg: str, strategy: StrategyTemplate = None, level: LOG_LEVEL = ...):
        pass

    def send_order(self, strategy: StrategyTemplate,
                   ab_symbol: str,
                   direction: Direction,
                   price: float,
                   volume: float,
                   offset: Offset,
                   order_type: OrderType) -> Iterable[str]:
        pass
    
    def cancel_order(self, strategy: StrategyTemplate, ab_orderid: str):
        pass

    def cancel_orders(self, strategy: StrategyTemplate, ab_orderids: Iterable[str]):
        pass
