import ast
import inspect
from abquant.trader.exception import MarketException
from copy import Error
from datetime import datetime, timedelta
from types import TracebackType
from collections import defaultdict
import sys
import traceback
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, List, Set, Tuple
from logging import ERROR, INFO, WARNING

from abquant.ordermanager import OrderManager
from abquant.trader.common import Direction, Interval, Offset, OrderType
from abquant.event import EventType, Event, EventDispatcher
from abquant.trader.object import CancelRequest, ContractData, HistoryRequest, LogData, OrderRequest, PositionData, SubscribeRequest
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.utility import OrderGrouper, extract_ab_symbol, round_to
from .template import StrategyTemplate

LOG_LEVEL = int


class LiveStrategyRunner:

    def __init__(self, event_dispatcher: EventDispatcher):
        self.event_dispatcher = event_dispatcher
        self.order_manager: OrderManager = self.event_dispatcher.order_manager

        self.strategies: Dict[str, StrategyTemplate] = {}

        self.symbol_strategys_map: Dict[str,
                                        List[StrategyTemplate]] = defaultdict(list)
        self.orderid_strategy_map: Dict[str, StrategyTemplate] = {}
        self.ab_tradeids: Set[str] = set()

        # maybe it is not the best place to call init.
        self.init()

    def add_strategy(
            self,
            strategy_class: type,
            strategy_name: str,
            ab_symbols: list,
            setting: dict):
        if strategy_name in self.strategies:
            self.write_log(
                "there is already a strategy named {} in this strategy runner".format(strategy_name))
            return
        self.compile_check(strategy_class)

        strategy = strategy_class(self, strategy_name, ab_symbols, setting)
        self.strategies[strategy_name] = strategy

        # Add vt_symbol to strategy map.
        for ab_symbol in ab_symbols:
            strategies = self.symbol_strategys_map[ab_symbol]
            strategies.append(strategy)

    def edit_strategy(self, strategy_name: str, setting: dict):
        strategy = self.strategies[strategy_name]
        strategy.update_setting(setting)

    def get_strategy(self, strategy_name: str):
        strategy = self.strategies.get(strategy_name, None)
        return strategy

    def remove_strategy(self, strategy_name: str):
        """
        not thread safe.
        """
        strategy = self.strategies[strategy_name]
        if strategy.trading:
            self.write_log(
                "strategy: {} can not be removed. stop it first".format(strategy_name))
            return

        # Remove from symbol strategy map
        for ab_symbol in strategy.ab_symbols:
            strategies = self.symbol_strategys_map[ab_symbol]
            strategies.remove(strategy)

        # Remove from ab_orderid strategy map
        for ab_orderid in strategy.active_orderids:
            if ab_orderid in self.orderid_strategy_map:
                self.orderid_strategy_map.pop(ab_orderid)

        # Remove from strategies
        self.strategies.pop(strategy_name)

    def init_strategy(self, strategy_name: str):
        """
        not thread safe 
        """
        strategy = self.strategies[strategy_name]

        if strategy.inited:
            self.write_log(
                "strategy: {} has alread inited. do not init again".format(strategy_name))
            return

        self.write_log("strategy: {} start to init ".format(strategy_name))

        # Call on_init function of strategy
        self.call_strategy_func(strategy, strategy.on_init)

        # Restore strategy data
        # see if required.

        gateway_names = set()

        for ab_symbol in strategy.ab_symbols:
            contract: ContractData = self.order_manager.get_contract(ab_symbol)
            if contract:
                req = SubscribeRequest(
                    symbol=contract.symbol, exchange=contract.exchange)
                self.order_manager.get_gateway(
                    contract.gateway_name).subscribe(req)
                gateway_names.add(contract.gateway_name)
            else:
                msg = "subscribe failed, can not find contract: {}. checkout if proper gateway connected well. sleep for several second before strategy init until async io done, and ab_symbol spell right.".format(
                    ab_symbol)
                self.write_log(
                    msg, strategy, level=ERROR)
                raise LookupError(msg)
        for gateway_name in gateway_names:
            self.order_manager.get_gateway(gateway_name).start()

        # Put event to update init completed status.
        strategy.inited = True
        self.write_log("strategy: {}, init success.".format(strategy_name))

    def start_strategy(self, strategy_name: str):
        """
        not threadsafe 
        """
        strategy = self.strategies[strategy_name]
        if not strategy.inited:
            self.write_log(
                "strategy: {} start failed,  init first.".format(strategy_name))
            return

        if strategy.trading:
            self.write_log(
                "strategy: {} have already started,  not need to start again.".format(strategy_name))
            return

        self.call_strategy_func(strategy, strategy.on_start)
        strategy.trading = True

    def stop_strategy(self, strategy_name: str):
        """
        not threadsafe 
        """
        strategy = self.strategies[strategy_name]
        if not strategy.trading:
            self.write_log(
                "strategy: {} have already in stop status,  not need to stop again.".format(strategy_name))
            return

        self.call_strategy_func(strategy, strategy.on_stop)
        strategy.trading = False
        strategy.cancel_all()

        # TODO record postion ?

    def init_all_strategies(self):
        """
        not threadsafe 
        """
        for strategy_name in self.strategies.keys():
            self.init_strategy(strategy_name)

    def start_all_strategies(self):
        """
        not threadsafe 
        """
        for strategy_name in self.strategies.keys():
            self.start_strategy(strategy_name)

    def stop_all_strategies(self):
        """
        not threadsafe 
        """
        for strategy_name in self.strategies.keys():
            self.stop_strategy(strategy_name)

    def init(self):
        self.register_event()

    def register_event(self):
        # register event to process_xx method
        self.event_dispatcher.register(
            EventType.EVENT_TICK, self.process_tick_event)
        self.event_dispatcher.register(
            EventType.EVENT_DEPTH, self.process_depth_event)
        self.event_dispatcher.register(
            EventType.EVENT_TRANSACTION, self.process_transaction_event)
        self.event_dispatcher.register(
            EventType.EVENT_ENTRUST, self.process_entrust_event)
        self.event_dispatcher.register(
            EventType.EVENT_ORDER, self.process_order_event)
        self.event_dispatcher.register(
            EventType.EVENT_TRADE, self.process_trade_event)
        # I do not think those are useful here.
        # self.event_dispatcher.register(
        #     EventType.EVENT_POSITION, self.process_position_event)
        # self.event_dispatcher.register(
        #     EventType.EVENT_ACCOUNT, self.process_account_event)
        # self.event_dispatcher.register(
        #     EventType.EVENT_CONTRACT, self.process_contract_event)
        self.event_dispatcher.register(
            EventType.EVENT_EXCEPTION, self.process_exception_event)
        self.event_dispatcher.register(
            EventType.EVENT_TIMER, self.process_timer_event)

    def process_timer_event(self, event: Event):
        """"""
        interval: int = event.data

        for _, strategy in self.strategies.items():
            if strategy.trading:
                self.call_strategy_func(strategy, strategy.on_timer, interval)

    def process_exception_event(self, event: Event):
        exception: Exception = event.data
        # for ab_symbol, strategys in self.symbol_strategys_map.items():
        # TODO
        strategies = None
        for _, strategy in self.strategies.items():
            if strategy.trading:
                self.call_strategy_func(
                    strategy, strategy.on_exception, exception)

    def process_tick_event(self, event: Event):
        """"""
        tick: TickData = event.data

        strategies = self.symbol_strategys_map[tick.ab_symbol]
        if not strategies:
            return

        for strategy in strategies:
            if strategy.inited:
                self.call_strategy_func(strategy, strategy.on_tick, tick)

    def process_depth_event(self, event: Event):
        """"""
        depth: DepthData = event.data

        strategies = self.symbol_strategys_map[depth.ab_symbol]
        if not strategies:
            return

        for strategy in strategies:
            if strategy.inited:
                self.call_strategy_func(strategy, strategy.on_depth, depth)

    def process_entrust_event(self, event: Event):
        """"""
        entrust: EntrustData = event.data

        strategies = self.symbol_strategys_map[entrust.ab_symbol]
        if not strategies:
            return

        for strategy in strategies:
            if strategy.inited:
                self.call_strategy_func(strategy, strategy.on_entrust, entrust)

    def process_transaction_event(self, event: Event):
        """"""
        transaction: TransactionData = event.data

        strategies = self.symbol_strategys_map[transaction.ab_symbol]
        if not strategies:
            return

        for strategy in strategies:
            if strategy.inited:
                self.call_strategy_func(
                    strategy, strategy.on_transaction, transaction)

    def process_order_event(self, event: Event):
        """"""
        order: OrderData = event.data

        # there may repeated order event.
        strategy = self.orderid_strategy_map.get(order.ab_orderid, None)
        if not strategy:
            return

        self.call_strategy_func(strategy, strategy.update_order, order)

    def process_trade_event(self, event: Event):
        """"""
        trade: TradeData = event.data

        # repeated trade event
        if trade.ab_tradeid in self.ab_tradeids:
            return
        self.ab_tradeids.add(trade.ab_tradeid)

        strategy = self.orderid_strategy_map.get(trade.ab_orderid, None)
        if not strategy:
            return

        self.call_strategy_func(strategy, strategy.update_trade, trade)

    def send_order(self,
                   strategy: StrategyTemplate,
                   ab_symbol: str,
                   direction: Direction,
                   price: float,
                   volume: float,
                   offset: Offset,
                   order_type: OrderType) -> Iterable[str]:

        contract: ContractData = self.order_manager.get_contract(ab_symbol)
        if not contract:
            self.write_log(f"委托失败，找不到合约：{ab_symbol}", strategy, level=ERROR)
            # TODO error
            return ""

        # Round order price and volume to nearest incremental value
        price = round_to(price, contract.pricetick)
        volume = round_to(volume, contract.min_volume)

        req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            offset=offset,
            type=order_type,
            price=price,
            volume=volume,
            reference=f"{strategy.strategy_name}"
        )

        ab_orderids = []

        ab_orderid = self.order_manager.get_gateway(
            contract.gateway_name).send_order(req)

        ab_orderids.append(ab_orderid)
        self.orderid_strategy_map[ab_orderid] = strategy

        return ab_orderids

    def cancel_order(self, strategy: StrategyTemplate, ab_orderid: str):
        order = self.order_manager.get_order(ab_orderid)
        if not order:
            self.write_log(f"撤单失败，找不到委托{ab_orderid}", strategy, level=WARNING)
            return

        req: CancelRequest = order.create_cancel_request()
        self.order_manager.get_gateway(
            order.gateway_name).cancel_order(req)

    def cancel_orders(self, strategy: StrategyTemplate, ab_orderids: Iterable[str]):
        order_grouper = OrderGrouper()
        # ab_orderids = set(ab_orderids)
        for ab_orderid in ab_orderids:
            order = self.order_manager.get_order(ab_orderid)
            if not order:
                self.write_log(
                    f"撤单失败，找不到委托{order.ab_orderid}", strategy, level=WARNING)
            else:
                order_grouper.add(order)

        for gateway_name, orders in order_grouper.items():
            reqs: List[CancelRequest] = [order.create_cancel_request()
                                         for order in orders]

            self.order_manager.get_gateway(
                gateway_name).cancel_orders(reqs)

    # I guess it is not necessary.
    # def cancel_all(self) ->None:
    #     pass

    def call_strategy_func(
        self, strategy: StrategyTemplate, func: Callable, params: Any = None
    ):
        """
        Call function of a strategy and catch any exception raised.
        """
        #  timer or something monitor decorator function could be here.
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            strategy.trading = False
            strategy.inited = False

            # et, ev, tb = sys.exc_info()
            msg = f"Exception in strategy: {strategy.strategy_name}. strategy stoped. \n{traceback.format_exc()}"
            self.write_log(msg, strategy, level=ERROR)

    def compile_check(self, strategy_class: type):
        for func_node in ast.walk(ast.parse(inspect.getsource(strategy_class))):
            if isinstance(func_node, ast.FunctionDef):
                for c in ast.walk(func_node):
                    if (isinstance(c, ast.Call) and
                        isinstance(c.func, ast.Attribute) and
                        c.func.attr == 'load_bars' and
                            func_node.name != 'on_init'):
                        raise AttributeError(
                            "strategy.load_bars, by which is only allowed to be called inside strategy.on_init method, called by {}.".format(func_node.name))

    # @lru_cache TO NOT USE lru_cache for situations dynamic adding and running strategies with data outdated risk.
    def load_bar(self, ab_symbol: str, days: int, interval: Interval) -> Iterable[BarData]:
        symbol, exchange = extract_ab_symbol(ab_symbol)
        end = datetime.now()
        start = end - timedelta(days=days)
        contract: ContractData = self.order_manager.get_contract(ab_symbol)
        data = []

        # Query bars from gateway if available
        if contract and contract.history_data:
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=start,
                end=end
            )
            data = self.order_manager.get_gateway(
                contract.gateway_name).query_history(req)
        else:
            data = None
        return data

    def load_bars(self,
                  strategy: StrategyTemplate,
                  days: int,
                  interval: Interval = Interval.MINUTE):
        ab_symbols = strategy.ab_symbols
        dts: Set[datetime] = set()
        history_data: Dict[Tuple, BarData] = {}

        # Load data from rqdata/gateway/database
        for ab_symbol in ab_symbols:
            data = self.load_bar(ab_symbol, days, interval)

            for bar in data:
                dts.add(bar.datetime)
                history_data[(bar.datetime, ab_symbol)] = bar
        dts = list(dts)
        dts.sort()
        bars = {}

        for dt in dts:
            for vt_symbol in ab_symbols:
                bar = history_data.get((dt, vt_symbol), None)
                if bar:
                    bars[vt_symbol] = bar
                elif vt_symbol in bars:
                    last_bar = bars[vt_symbol]

                    bar = BarData(
                        symbol=last_bar.symbol,
                        exchange=last_bar.exchange,
                        datetime=dt,
                        open_price=last_bar.close_price,
                        high_price=last_bar.close_price,
                        low_price=last_bar.close_price,
                        close_price=last_bar.close_price,
                        gateway_name=last_bar.gateway_name
                    )
                    bars[vt_symbol] = bar

            self.call_strategy_func(strategy, strategy.on_bars, bars)

    def write_log(self, msg: str, strategy: StrategyTemplate = None, level: LOG_LEVEL = INFO):
        if strategy:
            msg = f"{strategy.strategy_name}: {msg}"
        else:
            msg = f"StrategyRunner: {msg}"
        log = LogData(
            msg=msg, gateway_name=self.__class__.__name__, level=level)
        self.on_log(log)

    def on_log(self, log: LogData) -> None:
        event = Event(EventType.EVENT_LOG, log)
        self.event_dispatcher.put(event)

    def notify(self, msg: str, strategy: StrategyTemplate):
        # TODO
        raise NotImplementedError()