from abc import ABC, abstractmethod
from logging import INFO
from abquant.event.event import EventType
from typing import Iterable, Any, Set
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.event import EventDispatcher, Event
from abquant.trader.common import Exchange
from abquant.trader.object import AccountData, CancelRequest, ContractData, HistoryRequest, LogData, OrderRequest, PositionData, SubscribeMode, SubscribeRequest

class Gateway(ABC):
    default_setting = {}

    def __init__(self, event_dispatcher: EventDispatcher, gateway_name: str):
        self.event_dispatcher: EventDispatcher = event_dispatcher
        self.gateway_name: str = gateway_name
        self.subscribe_mode = SubscribeMode()

    def set_gateway_name(self, gateway_name: str):
        self.gateway_name = gateway_name

    def set_subscribe_mode(self, subscribe_mode: SubscribeMode):
        self.subscribe_mode = subscribe_mode
    
    def on_event(self, type: str, data: Any = None) -> None:
        event = Event(type, data)
        self.event_dispatcher.put(event)


    def write_log(self, msg: str, level = INFO) -> None:
        log = LogData(msg=msg, gateway_name=self.gateway_name, level=level)
        self.on_log(log)


    @abstractmethod
    def connect(self, setting: dict) -> None:
        """
        须确保 调用该函数式， 该交易所仓位信息，支持可交易品种，
         仓位信息， 交易所挂单情况都能够获取， 相应回调函数被调用
         """
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def subscribe(self, req: SubscribeRequest):
        pass

    @abstractmethod
    def start(self):
        """
        after start method called, the symbol subscribed by SubscribeRequest will start to receive.
        """
        pass

    @abstractmethod
    def send_order(self, order_request: OrderRequest) -> OrderData:
        pass
    
    @abstractmethod
    def cancel_order(self, cancel_request: CancelRequest) -> None:
        pass

        
    @abstractmethod
    def cancel_orders(self, reqs: Iterable[CancelRequest]) -> None:
        for req in reqs:
            self.cancel_order(req)

    @abstractmethod
    def query_account(self) -> Iterable[AccountData]:
        pass

    @abstractmethod
    def query_position(self) -> Iterable[PositionData]:
        pass

    @abstractmethod
    def query_history(self, req: HistoryRequest) -> Iterable[BarData]:
        pass

    def on_tick(self, tick: TickData) -> None:
        self.on_event(EventType.EVENT_TICK, tick)
    
    def on_transaction(self, transaction: TransactionData) -> None:
        self.on_event(EventType.EVENT_TRANSACTION, transaction)
    
    def on_entrust(self, entrust: EntrustData) -> None:
        self.on_event(EventType.EVENT_ENTRUST, entrust)

    def on_depth(self, depth: DepthData) -> None:
        self.on_event(EventType.EVENT_DEPTH, depth)

    def on_trade(self, trade: TradeData) -> None:
        self.on_event(EventType.EVENT_TRADE, trade)

    def on_order(self, order: OrderData) -> None:
        self.on_event(EventType.EVENT_ORDER, order)

    def on_position(self, position: PositionData) -> None:
        self.on_event(EventType.EVENT_POSITION, position)

    def on_account(self, account: AccountData) -> None:
        self.on_event(EventType.EVENT_ACCOUNT, account)

    def on_contract(self, contract: ContractData) -> None:
        self.on_event(EventType.EVENT_CONTRACT, contract)
        
    def on_log(self, log: LogData) -> None:
        self.on_event(EventType.EVENT_LOG, log)
