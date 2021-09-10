from typing import Iterable
from logging import INFO
from abquant.trader.common import Direction, Interval, Offset
from abquant.event import EventDispatcher

from .template import StrategyTemplate

LOG_LEVEL = int

class LiveStrategyRunner:

    def __init__(self, event_dispatcher: EventDispatcher):
        pass

    def init(self):
        pass

    def close(self):
        pass

    def register_event(self):
        # register event to process_xx method
        pass

    def process_xx(self, xx: xxDATA):
        pass

    def send_order(self,
                   strategy: StrategyTemplate,
                   ab_symbol: str,
                   direction: Direction,
                   offset: Offset,
                   price: float,
                   volume: float):
        pass

    def cancel_order(self, strategy: StrategyTemplate, ab_orderid: str):
        pass

    def cancel_orders(self, strategy: StrategyTemplate, ab_orderids: Iterable[str]):
        pass

    # I guess it is not necessary.
    # def cancel_all(self) ->None:
    #     pass

    def load_bars(self,
                  strategy: StrategyTemplate,
                  days: int,
                  interval: Interval = Interval.MINUTE):
        pass

    def add_strategy(
            self,
            strategy_class: type,
            strategy_name: str,
            ab_symbols: list,
            setting: dict):
        pass
    
    def edit_strategy(self, strategy_name: str, setting: dict):
        pass

    def get_strategy(self, strategy_name: str):
        pass

    def remove_strategy(self, strategy_name: str):
        pass

    def init_strategy(self, strategy_name: str):
        pass

    def start_strategy(self, strategy_name: str):
        pass

    def stop_strategy(self, strategy_name: str):
        pass

    def init_all_strategies(self):
        pass

    def stop_all_strategies(self):
        pass

    def write_log(self, msg: str, strategy: StrategyTemplate = None, level:LOG_LEVEL=INFO):
        pass
    
    def phone_call(self, msg: str, strategy: StrategyTemplate):
        pass
