from typing import Dict, Iterable, List, Tuple
from datetime import datetime

from pandas.tseries.offsets import Second
from abquant.ordermanager import OrderManager
from abquant.trader.common import Direction, Interval, Offset, OrderType
from abquant.trader.exception import MarketException
from abquant.event import EventType, Event, EventDispatcher
from abquant.trader.object import CancelRequest, ContractData, HistoryRequest, LogData, OrderRequest, PositionData, SubscribeRequest
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.utility import OrderGrouper, extract_ab_symbol, round_to
from .template import StrategyTemplate
from .strategyrunner import StrategyRunner, LOG_LEVEL
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
