from abc import ABC, abstractmethod
from abquant.event.dispatcher import Event
from copy import copy
from typing import Dict, Set, List, TYPE_CHECKING
from collections import defaultdict

from abquant.trader.common import Interval, Direction, Offset, OrderType
from abquant.trader.msg import BarData, TickData, OrderData, TradeData, TransactionData, EntrustData, DepthData

# TODO typechecking  and same thing in msg.py

from .strategyrunner import StrategyRunner
from .template import StrategyTemplate


class MinghangStrategyTemplate(StrategyTemplate):
    def __init__(
        self,
        strategy_runner: "StrategyRunner",
        strategy_name: str,
        ab_symbols: List[str],
        setting: dict,
    ):
        super(MinghangStrategyTemplate, self).__init__(strategy_runner, strategy_name, ab_symbols, setting)
    
    def cancel_symbol_order(self, ab_symbol: str):
        for ab_orderid, order in self.orders.items():
            if order.ab_orderid == ab_symbol:
                self.cancel_order(ab_orderid)

