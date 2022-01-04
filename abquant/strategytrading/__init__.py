from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import DefaultDict, Dict, List

from abquant.trader.common import Interval

from .template import StrategyTemplate
from .livestrategyrunner import LiveStrategyRunner


class BacktestingMode(Enum):
    BAR = "bar"
    TICK = "tick"
    Non = "live"


class BacktestParameter:
    def __init__(
        self,
        ab_symbols: List[str],
        interval: Interval,
        rates: Dict[str, float],
        slippages: Dict[str, float],
        sizes: Dict[str, float],
        priceticks: Dict[str, float],
        capital: int = 0,
        risk_free: float = 0,
        inverses: DefaultDict[str, bool] = defaultdict(lambda: False),
        mode: BacktestingMode = BacktestingMode.BAR,
        annual_days: int = 365,
    ):
        self.ab_symbols: List[str] = ab_symbols
        self.interval: Interval = interval

        self.rates: Dict[str, float] = rates
        self.slippages: Dict[str, float] = slippages
        self.sizes: Dict[str, float] = sizes
        self.priceticks: Dict[str, float] = priceticks

        self.capital: int = capital
        self.risk_free: float = risk_free
        self.inverse: DefaultDict[str, bool] = inverses

        self.mode: BacktestingMode = mode
        self.annual_days: int = annual_days

    # TODO checkout inverse 
    # def 

    def sub_parameter(self, ab_symbols: List[str]) -> "BacktestParameter":

        def sub_dict(keys, dict):
            sub_dict = {key: dict[key] for key in keys}
            return sub_dict

        return BacktestParameter(
            ab_symbols=ab_symbols,
            interval=self.interval,
            rates=sub_dict(ab_symbols, self.rates),
            slippages=sub_dict(ab_symbols, self.slippages),
            sizes=sub_dict(ab_symbols, self.sizes),
            priceticks=sub_dict(ab_symbols, self.priceticks),
            capital=self.capital,
            inverses=self.inverse,
            annual_days=self.annual_days,
            mode=self.mode
        )

# from .backteststrategyrunner import BacktestStrategyRunner