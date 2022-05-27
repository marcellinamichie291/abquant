import ast
from dataclasses import dataclass
import inspect
from copy import Error
from datetime import datetime, timedelta
from types import TracebackType
from collections import defaultdict
import sys
import traceback
import uuid
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, List, Set, Tuple
from logging import ERROR, INFO, WARNING

from abquant.ordermanager import OrderManager
from abquant.trader.common import Direction, Interval, Offset, OrderType
from abquant.trader.exception import MarketException
from abquant.event import EventType, Event, EventDispatcher
from abquant.trader.object import CancelRequest, ContractData, HistoryRequest, LogData, OrderRequest, PositionData, SubscribeRequest
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.utility import OrderGrouper, extract_ab_symbol, round_to
from .template import StrategyTemplate
from .strategyrunner import StrategyManager, StrategyRunner, LOG_LEVEL



class LiveStrategyRunner(StrategyRunner, StrategyManager):
    MAC = str(hex(uuid.getnode()))

    def __init__(self, event_dispatcher: EventDispatcher):
        super(LiveStrategyRunner, self).__init__()
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
        init_success = self.call_strategy_func(strategy, strategy.on_init)
        if not init_success:
            return
        # Restore strategy data
        # see if required.

        gateway_names = set()

        for ab_symbol in strategy.ab_symbols:
            contract: ContractData = self.order_manager.get_contract(ab_symbol)
            if contract:
                req = SubscribeRequest(
                    symbol=contract.symbol, exchange=contract.exchange, name=contract.name)
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
        self.monitor.send_status(strategy.run_id, "start", strategy.ab_symbols)
        self.monitor.send_struct(strategy.run_id, "strategy_status", "start")
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
        self.monitor.send_status(strategy.run_id, "stop", strategy.ab_symbols)
        self.monitor.send_struct(strategy.run_id, "strategy_status", "stop")
        strategy.trading = False
        strategy.cancel_all()


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
        self.timer_count: int = 0

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
        self.event_dispatcher.register(
            EventType.EVENT_LOG, self.process_log_event)
        self.event_dispatcher.register(
            EventType.EVENT_RAW, self.process_raw_event)

    def process_timer_event(self, event: Event):
        """"""
        interval: int = event.data
        new_timer_count = self.timer_count + interval
        for _, strategy in self.strategies.items():
            if strategy.trading:
                self.call_strategy_func(strategy, strategy.on_timer, interval)
                if (new_timer_count // 10) != self.timer_count // 10:
                    self.monitor.send_status(strategy.run_id, 'heartbeat', strategy.ab_symbols)
            
        self.timer_count = new_timer_count
                

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


    def process_log_event(self, event: Event):
        log: LogData = event.data
        if log.gateway_name == self.__class__.__name__:
            return
        self.monitor.send_log(self.MAC, log, log_type='system')

    def process_raw_event(self, event: Event):
        raw: Dict = event.data
        _type = raw.get('type')
        gateway_name = raw.get('gateway_name', 'default_gateway')
        if _type == 'status_websocket_user_connected':
            self.monitor.send_struct(self.MAC, "gateway_websocket_status", "start", gateway_name=gateway_name)
        elif _type == 'status_websocket_user_disconnected':
            self.monitor.send_struct(self.MAC, "gateway_websocket_status", "stop", gateway_name=gateway_name)
        elif _type == 'data_restful':
            _time = raw.get('time', None)
            if _time:
                dtype = raw.get('data_type', None)
                ftype = ("gateway_restful_interval" + "_" + dtype) if dtype else "gateway_restful_interval"
                self.monitor.send_struct(self.MAC, ftype, str(_time), gateway_name=gateway_name)

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
            order = strategy.orders.get(ab_orderid, None)
            if not order:
                self.write_log(
                    f"撤单失败，找不到交易单ab_orderid, {ab_orderid}, 通常来说，这意味着该orderid才刚发出，尚未获得交易所确认，或该order已成交或撤销。", strategy, level=WARNING)
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
    ) -> bool:
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
            self.monitor.send_status(strategy.run_id, "stop", strategy.ab_symbols)
            self.monitor.send_struct(strategy.run_id, "strategy_status", "stop")

            # et, ev, tb = sys.exc_info()
            msg = f"Exception in strategy: {strategy.strategy_name}. strategy stoped. \n{traceback.format_exc()}"
            self.write_log(msg, strategy, level=ERROR)
            return False
        return True

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

    def load_bar_(self, ab_symbol: str, start: datetime, end: datetime, interval: Interval) -> Iterable[BarData]:
        symbol, exchange = extract_ab_symbol(ab_symbol)
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
            raise ConnectionError("contract is not found or history_data is not set.")
        return data


    def load_bars_warm_up(self,
                  strategy: StrategyTemplate,
                  start: datetime,
                  end: datetime,
                  interval: Interval = Interval.MINUTE, 
                  on_interval: Callable[[Dict[str, BarData]], None]=None):

        ab_symbols = strategy.ab_symbols
        dts: Set[datetime] = set()
        history_data: Dict[Tuple, BarData] = {}       

        for ab_symbol in ab_symbols:
            data = self.load_bar_(ab_symbol, start, end, interval)

            for bar in data:
                dts.add(bar.datetime)
                history_data[(bar.datetime, ab_symbol)] = bar
        dts = list(dts)
        dts.sort()
        bars = {}

        for dt in dts:
            for ab_symbol in ab_symbols:
                bar = history_data.get((dt, ab_symbol), None)
                if bar:
                    bars[ab_symbol] = bar
                elif ab_symbol in bars:
                    last_bar = bars[ab_symbol]

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
                    bars[ab_symbol] = bar

            if not on_interval or interval == Interval.MINUTE:
                if on_interval:
                    self.write_log("call load_bar in 1 min Interval, will automatically call strategy.on_bars, the parameter on_interval will not be used.", strategy, WARNING)
                self.call_strategy_func(strategy, strategy.on_bars, bars)
            else:
                raise NotImplementedError("non-minute-interval load_bars are not supported yet.")
        
 


    def load_bars(self,
                  strategy: StrategyTemplate,
                  days: int,
                  interval: Interval = Interval.MINUTE, on_interval: Callable[[Dict[str, BarData]], None]=None):
        end = datetime.now()
        start = end - timedelta(days=days)
        # Load data from gateway/database
        self.load_bars_warm_up(strategy, start, end, interval, on_interval)
        self.load_bars_warm_up(strategy, end, datetime.now(), interval, on_interval)

           

    def write_log(self, msg: str, strategy: StrategyTemplate = None, level: LOG_LEVEL = INFO):
        if strategy:
            msg = f"{strategy.strategy_name}: {msg}"
            self.monitor.send_log(strategy.run_id, LogData(gateway_name=self.__class__.__name__, msg=msg, level=level))

        else:
            msg = f"StrategyRunner: {msg}"
            self.monitor.send_log(self.MAC, LogData(gateway_name=self.__class__.__name__, msg=msg, level=level))
        log = LogData(
            msg=msg, gateway_name=self.__class__.__name__, level=level)
        self.on_log(log)

    def on_log(self, log: LogData) -> None:
        event = Event(EventType.EVENT_LOG, log)
        self.event_dispatcher.put(event)

    def notify_lark(self, strategy: StrategyTemplate, msg):
        # notify lark
        self.monitor.send_notify_lark(strategy.run_id, msg)
