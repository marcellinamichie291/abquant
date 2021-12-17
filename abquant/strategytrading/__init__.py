from enum import ENUM

from .template import StrategyTemplate
from .livestrategyrunner import LiveStrategyRunner
from .backteststrategyrunner import BacktestStrategyRunner



class BacktestingMode(ENUM):
    BAR = "bar"
    TICK = "tick"
    Non = "live"