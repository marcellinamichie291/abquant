from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Tuple
from datetime import datetime

from pandas.tseries.offsets import Second
from abquant.ordermanager import OrderManager
from abquant.strategytrading import replayrunner
from abquant.strategytrading.replayrunner import ReplayRunner
from abquant.trader.common import Direction, Interval, Offset, OrderType
from abquant.trader.exception import MarketException
from abquant.event import EventType, Event, EventDispatcher
from abquant.trader.object import CancelRequest, ContractData, HistoryRequest, LogData, OrderRequest, PositionData, SubscribeRequest
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.utility import OrderGrouper, extract_ab_symbol, round_to
from abquant.dataloader import DataLoader
from . import BacktestParameter, BacktestingMode
from .template import StrategyTemplate
from .strategyrunner import StrategyManager, StrategyRunner, LOG_LEVEL




class BacktestStrategyRunner(StrategyManager):
    def __init__(self) -> None:
        self.strategies: Dict[str, StrategyTemplate] = {}
        self.replay_runner: Dict[str, ReplayRunner] = {}
        self.data_loader: DataLoader = None
        self.parameter: BacktestParameter = None

    def set_data_loader(self, data_loader: DataLoader):
        self.data_loader = data_loader
    
    def set_parameter(self, backtest_parameter: BacktestParameter):
        self.parameter = backtest_parameter

    def add_strategy(self, strategy_class: type, strategy_name: str, ab_symbols: list, setting: dict) -> None:
        if self.strategies:
            raise NotImplementedError(
                "only 1 strategy instance backtesting is supported")

        try:
            sub_parameter = self.parameter.sub_parameter(ab_symbols)
        except KeyError as e:
            raise KeyError(f"{e} is not in backtest parameter")
        replay_runner = ReplayRunner(
                ab_symbols=ab_symbols,
                interval=sub_parameter.interval,
                rates=sub_parameter.rates,
                slippages=sub_parameter.slippages,
                sizes=sub_parameter.sizes,
                priceticks=sub_parameter.priceticks,
                capital=sub_parameter.capital,
                inverse=sub_parameter.inverse,
                annual_days=sub_parameter.annual_days,
                mode=sub_parameter.mode,
        )
        strategy = strategy_class(replay_runner, strategy_name, ab_symbols, setting)
        self.strategies[strategy_name] = strategy

        self.replay_runner[strategy_name] = replay_runner

    def remove_strategy(self, strategy_name: str):
        self.strategies.pop(strategy_name)
        self.replay_runner.pop(strategy_name)

    def get_strategy(self, strategy_name: str):
        strategy = self.strategies.get(strategy_name, None)
        return strategy

    def edit_strategy(self, strategy_name: str, setting: dict):
        strategy = self.strategies[strategy_name]
        strategy.update_setting(setting)

    # TODO ret
    def run_backtest(self, start_dt: datetime, end_dt: datetime, interval: Interval = Interval.MINUTE, output_log: bool=False):
        assert interval == Interval.MINUTE, "for now, only Minute interval backtest are supported. Tick level may supported later."
        if self.data_loader is None:
            raise AttributeError("data_loader is not set")
        while self.strategies:
            strategy_name, strategy = self.strategies.popitem()
            ab_symbols = strategy.ab_symbols
            
            replay_runner = self.replay_runner.pop(strategy_name)
            replay_runner.set_data_loader(self.data_loader)
          
            # TODO
            # replay_runner.add_strategy()
            replay_runner.set_strategy(strategy)
            replay_runner.load_data(start_dt, end_dt)

            print("load data done========================")
            replay_runner.run_backtesting(output_log)
            print("simulate matching done========================")
            df = replay_runner.calculate_result()
            print("calculate done========================")
            replay_runner.calculate_statistics(df)
            print("calculate static done========================")
