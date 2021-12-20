from enum import Enum

from .template import StrategyTemplate
from .livestrategyrunner import LiveStrategyRunner
from .backteststrategyrunner import BacktestStrategyRunner



class BacktestingMode(Enum):
    BAR = "bar"
    TICK = "tick"
    Non = "live"