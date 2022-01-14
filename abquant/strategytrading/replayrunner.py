from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from copy import copy, deepcopy
from logging import INFO
import traceback
from pandas import DataFrame
import numpy as np
from typing import DefaultDict, Dict, Iterable, List, Set, Tuple, Union
from datetime import date, datetime, timedelta
import sys
import ast
import inspect

from abquant.dataloader import DataLoader
from abquant.dataloader.dataloader import Dataset
from abquant.orderbook.orderbook import OrderBook
from abquant.ordermanager import OrderManager
from abquant.trader.common import Direction, Interval, Offset, OrderType, Status
from abquant.trader.exception import MarketException
from abquant.event import EventType, Event, EventDispatcher
from abquant.trader.object import CancelRequest, ContractData, HistoryRequest, LogData, OrderRequest, PositionData, SubscribeRequest
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.utility import OrderGrouper, extract_ab_symbol, round_to

from . import BacktestingMode
from .template import StrategyTemplate
from .strategyrunner import StrategyRunner, LOG_LEVEL
from .result import ContractDailyResult, ContractsDailyResult










class ReplayRunner(StrategyRunner):
    """"""

    gateway_name = "BACKTESTING"

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
        inverse: DefaultDict[str, bool] = defaultdict(lambda: False),
        mode: BacktestingMode = BacktestingMode.BAR,
        annual_days: int = 365,
        # TODO
    ) -> None:
        """"""

        super(ReplayRunner, self).__init__()
        self.ab_symbols: List[str] = ab_symbols

        self.interval: Interval = interval
        self.rates: Dict[str, float] = rates
        self.slippages: Dict[str, float] = slippages
        self.sizes: Dict[str, float] = sizes
        self.priceticks: Dict[str, float] = priceticks

        self.start: datetime = None
        self.end: datetime = None
        self.capital: int = capital
        self.risk_free: float = risk_free
        self.inverse: DefaultDict[str, bool] = inverse

        self.mode: BacktestingMode = mode
        self.annual_days: int = annual_days

        self.strategy: StrategyTemplate = None
        self.datetime: datetime = None

        if interval == Interval.MINUTE and mode == BacktestingMode.BAR:
            self.order_book = OrderBook.orderbook_factory('Bar')
        else:
            raise ValueError(
                "Backtest are only supported for 1 minute interval and Bar mode for now.")

        self.days: int = 0
        self.history_data: Dict[Tuple, BarData] = {}
        self.dts: Set[datetime] = set()

        self.limit_order_count = 0
        self.limit_orders = {}
        # self.active_limit_orders = {}

        # self.trade_count = 0
        self.trades: Dict[str, TradeData] = {}

        self.logs = []

        self.daily_results: Dict[date, ContractsDailyResult] = {}
        self.daily_df = None

    # def set_strategy(self, strategy_class: type, setting: dict, strategy_name: str = None) -> None:
    #     """"""
    #     self.strategy = strategy_class(
    #         self, strategy_class.__name__ if strategy_name is not None else strategy_name, copy(
    #             self.ab_symbols), setting
    #     )

    def set_strategy(self, strategy: StrategyTemplate) -> None:
        """"""
        self.strategy = strategy
        self.compile_check(strategy.__class__)

    def set_data_loader(self, data_loader: DataLoader):
        self.data_loader: DataLoader = data_loader

    def load_bar_data(self, ab_symbol, interval, start, end) -> Dataset:
        data = self.data_loader.load_data(ab_symbol, start, end)
        # data: Dataset = self.data_loader[ab_symbol]

        # if data.start != start:
        #     self.output("加载数据，起始时间异常")
        #     return
        # if end != data.end:
        #     self.output("加载数据，终止时间异常")
        #     return
        # if data[0].interval != Interval.MINUTE:
        #     self.output("barData必须为分钟级")
        #     return
        return data

    def compile_check(self, strategy_class: type):
        for func_node in ast.walk(ast.parse(inspect.getsource(strategy_class))):
            if isinstance(func_node, ast.FunctionDef):
                if func_node.name in ('on_timer', 'on_entrust', 'on_transaction', 'on_depth', 'on_tick'):
                    show_flag = False
                    for c in ast.walk(func_node):
                        if isinstance(c, (ast.Call, ast.Assign)):
                            show_flag = True
                    if show_flag:
                        self.output("WARNING: strategy {} 的method {} 在回测中不会被调用, 即如果该函数中有除了合成bar之外的逻辑，如算因子或下单，那么回测结果可能与实盘迥异。".format(
                            self.strategy.strategy_name, func_node.name))

                if func_node.name in ('update_order', 'update_trade'):
                    show_flag = False
                    for c in ast.walk(func_node):
                        # TODO
                        pass
                        # if isinstance(c, ast.Call):#, ast.Assign)):
                        #     show_flag = True
                    if show_flag:
                        self.output("WARNING: strategy {} 的function {} 在回测中不会被调用, 即如果该函数中有除了合成bar之外的逻辑，如算因子或下单，那么回测结果可能与实盘迥异。".format(
                            self.strategy.strategy_name, func_node.name))

                for c in ast.walk(func_node):
                    if (isinstance(c, ast.Call) and
                        isinstance(c.func, ast.Attribute) and
                        c.func.attr == 'load_bars' and
                            func_node.name != 'on_init'):
                        raise AttributeError(
                            "strategy.load_bars, by which is only allowed to be called inside strategy.on_init method, called by {}.".format(func_node.name))

    def load_data(self, start_dt: datetime, end_dt: datetime) -> None:
        """"""
        self.output("开始加载历史数据")
        self.start = start_dt
        self.end = end_dt

        if not self.end:
            self.end = datetime.now()

        if self.start >= self.end:
            self.output("起始日期必须小于结束日期")
            return

        # Clear previously loaded history data
        self.history_data.clear()
        self.dts.clear()

        # Load 30 days of data each time and allow for progress update
        progress_delta = timedelta(days=1)
        total_delta = self.end - self.start
        interval_delta = timedelta(minutes=1)

        for ab_symbol in self.ab_symbols:
            start = self.start
            end = self.start + progress_delta
            progress = 0

            data_count = 0
            while start < self.end:
                # Make sure end time stays within set range
                end = min(end, self.end)

                if self.mode == BacktestingMode.BAR:
                    data: Iterable[BarData] = self.load_bar_data(
                        ab_symbol,
                        self.interval,
                        start,
                        end
                    )
                    for bar in data:
                        self.dts.add(bar.datetime)
                        self.history_data[(bar.datetime, ab_symbol)] = bar
                        data_count += 1

                else:
                    pass
                    # data = self.load_tick_data(ab_symbol,
                    #                       start,
                    #                       end
                    #                       )
                    # for tick in data:
                    #     self.dts.add(tick.datetime)
                    #     self.history_data[(tick.datetime, ab_symbol)] = tick
                    #     data_count += 1

                progress += progress_delta / total_delta
                progress = min(progress, 1)
                progress_bar = "#" * int(progress * 10)
                self.output(f"{ab_symbol}加载进度:{progress_bar} [{progress:.0%}]")

                start = end
                end += (progress_delta)

            self.output(f"{ab_symbol}历史数据加载完成，数据天数:{data_count}")

        self.output("所有历史数据加载完成")

    def run_backtesting(self, log=False) -> None:
        """"""
        self.strategy.on_init()

        # Generate sorted datetime list
        dts = list(self.dts)
        dts.sort()

        # Use the first [days] of history data for initializing strategy
        day_count = 0
        ix = 0

        for ix, dt in enumerate(dts):
            if self.datetime and dt.day != self.datetime.day:
                day_count += 1
                if day_count >= self.days:
                    break
            try:
                if self.mode == BacktestingMode.BAR:

                    self.new_bars(dt)
                else:
                    self.new_ticks(dt)
            except Exception:
                self.output("触发异常，回测终止")
                self.output(traceback.format_exc())
                return

        self.strategy.inited = True
        self.output("策略初始化完成")

        self.strategy.on_start()
        self.strategy.trading = True
        self.output("开始回放历史数据")

        # Use the rest of history data for running backtesting
        for dt in dts[ix:]:
            try:
                if self.mode == BacktestingMode.BAR:
                    self.new_bars(dt)
                else:
                    self.new_ticks(dt)

            except Exception:
                self.output("触发异常，回测终止")
                self.output(traceback.format_exc())
                return

        self.strategy.on_stop()
        self.output("历史数据回放结束")
        if log:
            for log in self.logs:
                self.output(log)

    def update_daily_close(self, bars: Union[Dict[str, BarData], TickData], dt: datetime) -> None:
        """"""
        d = dt.date()

        close_prices = {}
        if not isinstance(bars, Dict):
            if bars.trace_price != 0:
                close_prices[bars.ab_symbol] = bars.trade_price
            else:
                return
        else:
            for bar in bars.values():
                close_prices[bar.ab_symbol] = bar.close_price

        daily_result = self.daily_results.get(d, None)
        # print("type", type(bars), "update dayly close", close_prices)
        if daily_result:
            daily_result.update_close_prices(close_prices)
        else:
            self.daily_results[d] = ContractsDailyResult(d, close_prices)

    def new_bars(self, dt: datetime) -> None:
        """"""
        self.datetime = dt

        # self.bars.clear()
        for ab_symbol in self.ab_symbols:
            bar = self.history_data.get((dt, ab_symbol), None)

            # If bar data of ab_symbol at dt exists
            if not bar and ab_symbol in self.order_book.newest_bars():
                old_bar = self.order_book.newest_bars()[ab_symbol]

                bar = BarData(
                    symbol=old_bar.symbol,
                    exchange=old_bar.exchange,
                    datetime=dt,
                    open_price=old_bar.close_price,
                    high_price=old_bar.close_price,
                    low_price=old_bar.close_price,
                    close_price=old_bar.close_price,
                    gateway_name=old_bar.gateway_name
                )
                self.output("There is a bar data of {} at {} missed. Use the last bar close_price instead.".format(ab_symbol, dt))
            # self.bars[ab_symbol] = bar
            if bar is None:
                raise TypeError("There is a bar data of {} at {} missed.".format(ab_symbol, dt))
            self.order_book.update_bar(bar)

        for order in self.order_book.accept_submitting_orders():
            self.strategy.update_order(order)
        for order, trade in self.order_book.match_orders():
            self.strategy.update_order(order)
            self.strategy.update_trade(trade)
            self.trades[trade.ab_tradeid] = trade
        self.strategy.on_bars(self.order_book.newest_bars())
        # self.submiting_order()
        for order in list(self.order_book.submitting_orders()):
            self.strategy.update_order(order)

        self.update_daily_close(self.order_book.newest_bars(), dt)

    def new_ticks(self, dt: datetime) -> None:
        pass
    #     self.datetime = dt

    #     # self.bars.clear()
    #     for ab_symbol in self.ab_symbols:
    #         tick = self.history_data.get((dt, ab_symbol), None)

    #         # If bar data of ab_symbol at dt exists
    #         if tick:
    #             self.tick = tick

    #             self.strategy.on_tick(tick)

    #             self.update_daily_close(self.tick, dt)

    def load_bars(
        self,
        strategy: StrategyTemplate,
        days: int,
        interval: Interval
    ) -> None:
        """"""
        self.days += days
        if (self.end - self.start) <= timedelta(days=self.days):
            raise ValueError(
                "days of backtesting duration is less than days in data warm up( staregyTemplate.load_bars(days) ).")

    def submiting_order(self):
        """"""
        for order in list(self.order_book.submitting_orders()):
            self.strategy.update_order(order)

    def send_order(
        self,
        strategy: StrategyTemplate,
        ab_symbol: str,
        direction: Direction,
        price: float,
        volume: float,
        offset: Offset,
        # TODO markorder
        order_type: OrderType
    ) -> List[str]:
        """"""
        price = round_to(price, self.priceticks[ab_symbol])
        if volume == 0:
            # TODO rejected
            self.output(" WARNING! order's volumn is not allowed to be 0")
        symbol, exchange = extract_ab_symbol(ab_symbol)

        self.limit_order_count += 1

        order = OrderData(
            symbol=symbol,
            exchange=exchange,
            orderid=str(self.limit_order_count),
            direction=direction,
            offset=offset,
            price=price,
            volume=volume,
            status=Status.SUBMITTING,
            datetime=self.datetime,
            gateway_name=self.gateway_name,
        )

        self.order_book.insert_order(order)
        self.limit_orders[order.ab_orderid] = order

        return [order.ab_orderid]

    def cancel_order(self, strategy: StrategyTemplate, ab_orderid: str) -> None:
        """
        Cancel order by ab_orderid.
        """
        # if ab_orderid not in self.active_limit_orders:
        #     return

        # order.status = Status.CANCELLED
        order = self.order_book.cancel_order(ab_orderid)
        if order is not None:
            self.strategy.update_order(order)

    def cancel_orders(self, strategy: StrategyTemplate, ab_orderids: Iterable[str]):
        order_grouper = OrderGrouper()
        # ab_orderids = set(ab_orderids)
        for ab_orderid in ab_orderids:
            self.cancel_order(strategy, ab_orderid)

    def write_log(self, msg: str, strategy: StrategyTemplate = None, level=INFO) -> None:
        """
        Write log message.
        """
        msg = f"{self.datetime}\t{msg}"
        self.logs.append(msg)

    def notify_lark(self, strategy: StrategyTemplate, msg: str):
        # TODO
        pass

    def sync_strategy_data(self, strategy: StrategyTemplate) -> None:
        """
        """
        pass

    def output(self, msg) -> None:
        """
        Output message of backtesting engine.
        """
        print(f"{datetime.now()}\t{msg}")
    
    def sorted_trades(self):
        return sorted(self.trades.values(), key= lambda x: x.datetime)
    
    def sorted_daily_results(self):
        return sorted(self.daily_results.values(), key=lambda x: x.date)

    def calculate_result(self) -> DataFrame:
        """"""
        self.output("开始计算逐日盯市盈亏")

        if not self.trades:
            self.output("成交记录为空，无法计算")
            return

        # Add trade data into daily reuslt.
        for trade in self.trades.values():
            d = trade.datetime.date()
            daily_result = self.daily_results[d]
            daily_result.add_trade(trade)

        # Calculate daily result by iteration.
        pre_closes = {}
        start_poses = {}

        for daily_result in self.daily_results.values():
            daily_result.calculate_pnl(
                pre_closes,
                start_poses,
                self.sizes,
                self.rates,
                self.slippages,
                self.inverse
            )

            pre_closes = daily_result.close_prices
            start_poses = daily_result.end_poses

        # Generate dataframe
        results = defaultdict(list)

        for daily_result in self.daily_results.values():
            fields = [
                "date", "trade_count", "turnover",
                "commission", "slippage", "trading_pnl",
                "holding_pnl", "total_pnl", "net_pnl"
            ]
            for key in fields:
                value = getattr(daily_result, key)
                results[key].append(value)

        self.daily_df = DataFrame.from_dict(results).set_index("date")

        self.output("逐日盯市盈亏计算完成")
        return self.daily_df

    def calculate_statistics(self, df: DataFrame = None, output=True) -> None:
        """"""
        self.output("开始计算策略统计指标")

        # Check DataFrame input exterior
        if df is None:
            df = self.daily_df

        # Check for init DataFrame
        if df is None:
            # Set all statistics to 0 if no trade.
            start_date = ""
            end_date = ""
            total_days = 0
            profit_days = 0
            loss_days = 0
            end_balance = 0
            max_drawdown = 0
            max_ddpercent = 0
            max_drawdown_duration = 0
            total_net_pnl = 0
            daily_net_pnl = 0
            total_commission = 0
            daily_commission = 0
            total_slippage = 0
            daily_slippage = 0
            total_turnover = 0
            daily_turnover = 0
            total_trade_count = 0
            daily_trade_count = 0
            total_return = 0
            annual_return = 0
            daily_return = 0
            return_std = 0
            sharpe_ratio = 0
            return_drawdown_ratio = 0
        else:
            # Calculate balance related time series data
            df["balance"] = df["net_pnl"].cumsum() + self.capital
            # TODO
            df["return"] = np.log(
                df["balance"] / df["balance"].shift(1)).fillna(0)
            df["highlevel"] = (
                df["balance"].rolling(
                    min_periods=1, window=len(df), center=False).max()
            )
            df["drawdown"] = df["balance"] - df["highlevel"]
            df["ddpercent"] = df["drawdown"] / df["highlevel"] * 100

            # Calculate statistics value
            start_date = df.index[0]
            end_date = df.index[-1]

            total_days = len(df)
            profit_days = len(df[df["net_pnl"] > 0])
            loss_days = len(df[df["net_pnl"] < 0])

            end_balance = df["balance"].iloc[-1]
            max_drawdown = df["drawdown"].min()
            max_ddpercent = df["ddpercent"].min()
            max_drawdown_end = df["drawdown"].idxmin()

            if isinstance(max_drawdown_end, date):
                max_drawdown_start = df["balance"][:max_drawdown_end].idxmax()
                max_drawdown_duration = (
                    max_drawdown_end - max_drawdown_start).days
            else:
                max_drawdown_duration = 0

            total_net_pnl = df["net_pnl"].sum()
            daily_net_pnl = total_net_pnl / total_days

            total_commission = df["commission"].sum()
            daily_commission = total_commission / total_days

            total_slippage = df["slippage"].sum()
            daily_slippage = total_slippage / total_days

            total_turnover = df["turnover"].sum()
            daily_turnover = total_turnover / total_days

            total_trade_count = df["trade_count"].sum()
            daily_trade_count = total_trade_count / total_days

            total_return = (end_balance / self.capital - 1) * 100
            annual_return = total_return / total_days * self.annual_days
            daily_return = df["return"].mean() * 100
            return_std = df["return"].std() * 100

            if return_std:
                daily_risk_free = self.risk_free / np.sqrt(self.annual_days)
                sharpe_ratio = (daily_return - daily_risk_free) / \
                    return_std * np.sqrt(self.annual_days)
            else:
                sharpe_ratio = 0

            return_drawdown_ratio = -total_net_pnl / max_drawdown

        # Output
        if output:
            self.output("-" * 30)
            self.output(f"首个交易日:\t{start_date}")
            self.output(f"最后交易日:\t{end_date}")

            self.output(f"总交易日:\t{total_days}")
            self.output(f"盈利交易日:\t{profit_days}")
            self.output(f"亏损交易日:\t{loss_days}")

            self.output(f"起始资金:\t{self.capital:,.2f}")
            self.output(f"结束资金:\t{end_balance:,.2f}")

            self.output(f"总收益率:\t{total_return:,.2f}%")
            self.output(f"年化收益:\t{annual_return:,.2f}%")
            self.output(f"最大回撤: \t{max_drawdown:,.2f}")
            self.output(f"百分比最大回撤: {max_ddpercent:,.2f}%")
            self.output(f"最长回撤天数: \t{max_drawdown_duration}")

            self.output(f"总盈亏:\t{total_net_pnl:,.2f}")
            self.output(f"总手续费:\t{total_commission:,.2f}")
            self.output(f"总滑点:\t{total_slippage:,.2f}")
            self.output(f"总成交金额:\t{total_turnover:,.2f}")
            self.output(f"总成交笔数:\t{total_trade_count}")

            self.output(f"日均盈亏:\t{daily_net_pnl:,.2f}")
            self.output(f"日均手续费:\t{daily_commission:,.2f}")
            self.output(f"日均滑点:\t{daily_slippage:,.2f}")
            self.output(f"日均成交金额:\t{daily_turnover:,.2f}")
            self.output(f"日均成交笔数:\t{daily_trade_count}")

            self.output(f"日均收益率:\t{daily_return:,.2f}%")
            self.output(f"收益标准差:\t{return_std:,.2f}%")
            self.output(f"Sharpe Ratio:\t{sharpe_ratio:,.2f}")
            self.output(f"收益回撤比:\t{return_drawdown_ratio:,.2f}")

        statistics = {
            "start_date": start_date,
            "end_date": end_date,
            "total_days": total_days,
            "profit_days": profit_days,
            "loss_days": loss_days,
            "capital": self.capital,
            "end_balance": end_balance,
            "max_drawdown": max_drawdown,
            "max_ddpercent": max_ddpercent,
            "max_drawdown_duration": max_drawdown_duration,
            "total_net_pnl": total_net_pnl,
            "daily_net_pnl": daily_net_pnl,
            "total_commission": total_commission,
            "daily_commission": daily_commission,
            "total_slippage": total_slippage,
            "daily_slippage": daily_slippage,
            "total_turnover": total_turnover,
            "daily_turnover": daily_turnover,
            "total_trade_count": total_trade_count,
            "daily_trade_count": daily_trade_count,
            "total_return": total_return,
            "annual_return": annual_return,
            "daily_return": daily_return,
            "return_std": return_std,
            "sharpe_ratio": sharpe_ratio,
            "return_drawdown_ratio": return_drawdown_ratio,
        }

        # Filter potential error infinite value
        for key, value in statistics.items():
            if value in (np.inf, -np.inf):
                value = 0
            statistics[key] = np.nan_to_num(value)

        self.output("策略统计指标计算完成")
        return statistics
