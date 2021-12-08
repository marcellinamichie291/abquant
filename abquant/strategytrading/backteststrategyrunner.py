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
from abquant.dataloader import DataLoader
from .template import StrategyTemplate
from .strategyrunner import StrategyManager, StrategyRunner, LOG_LEVEL

class BacktestStrategyRunner(StrategyManager):
    def __init__(self) -> None:
        self.strategies: Dict[str, StrategyTemplate] = {}
        self.data_loader: DataLoader = None

    def set_data_loader(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def add_strategy(self, strategy_class: type, strategy_name: str, ab_symbols: list, setting: dict) -> None:
        if self.strategies:
            raise NotImplementedError("only 1 strategy instance backtesting is supported")
        strategy = strategy_class(self, strategy_name, ab_symbols, setting)
        self.strategies[strategy_name] = strategy


    def remove_strategy(self, strategy_name: str):
        self.strategies.pop(strategy_name)

    def get_strategy(self, strategy_name: str):
        strategy = self.strategies.get(strategy_name, None)
        return strategy

    def edit_strategy(self, strategy_name: str, setting: dict):
        strategy = self.strategies[strategy_name]
        strategy.update_setting(setting)

    def run_backtest(self, start_dt: datetime, end_dt: datetime, interval: Interval = Interval.MINUTE):
        assert(interval==Interval.MINUTE, "for now, only Minute interval backtest are supported. Tick level may supported later.")
        if self.data_loader is None:
            raise AttributeError("data_loader is not set")
        strategy_name, strategy = self.strategies.popitem()
        
