from typing import Dict, List
from copy import copy

from ...event.event import EventType
from ...event.dispatcher import Event
from ...trader.msg import BarData
from ...trader.object import (
    OrderData,
    CancelRequest,
    HistoryRequest,
    OrderRequest,
    PositionData,
    SubscribeRequest,
    HistoryRequest,
)
from ...event import EventDispatcher
from ...trader.common import Exchange
from ...gateway.basegateway import Gateway
from .dydx_accessor import DydxAccessor
from .dydx_listener import DydxWebsocketListener
from .dydx_util import api_key_credentials_map


# test 和官方客户端对比
# from dydx3.modules.private import Private


class DydxGateway(Gateway):
    default_setting = {
        "key": "",
        "secret": "",
        "passphrase": "",
        "stark_private_key": "",
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["TESTNET", "REAL"],
        "limitFee": 0.0005,  # makerFeeRate: 0.00050 or takerFeeRate: takerFeeRate: 0.00100
        "accountNumber": 0
    }
    exchanges: Exchange = [Exchange.DYDX]

    def __init__(self, event_dispatcher: EventDispatcher, gateway_name="DYDX"):
        super().__init__(event_dispatcher, gateway_name)
        self.set_gateway_name(gateway_name)

        self.market_listener = DydxWebsocketListener(self)
        self.rest_accessor = DydxAccessor(self)

        self.posid: str = "1"
        self.id: str = ""
        self.count: int = 0
        self.sys_local_map: Dict[str, str] = {}
        self.local_sys_map: Dict[str, str] = {}

        self.orders: Dict[str, OrderData] = {}
        self.positions: Dict[str, PositionData] = {}

    def connect(self, setting: dict) -> None:
        """连接"""

        api_key_credentials_map["key"] = setting["key"]
        api_key_credentials_map["secret"] = setting["secret"]
        api_key_credentials_map["passphrase"] = setting["passphrase"]
        api_key_credentials_map["stark_private_key"] = setting["stark_private_key"]
        server: str = setting["test_net"]
        proxy_host: str = setting["proxy_host"]
        proxy_port: int = setting["proxy_port"]
        limitFee: float = setting["limitFee"]
        accountNumber: str = setting["accountNumber"]

        self.rest_accessor.connect(server, proxy_host, proxy_port, limitFee)
        self.market_listener.connect(
            proxy_host, proxy_port, server, accountNumber)
        self.event_dispatcher.register(
            EventType.EVENT_TIMER, self.process_timer_event)
        self.on_gateway(self)

    def start(self):
        self.market_listener.start()

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.market_listener.subscribe(req)

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        return self.rest_accessor.send_order(req)

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        self.rest_accessor.cancel_order(req)

    def cancel_orders(self, reqs) -> None:
        for req in reqs:
            self.cancel_order(req)

    def query_account(self) -> None:
        """查询资金"""
        self.rest_accessor.query_account()

    def query_position(self) -> None:
        """查询持仓"""
        pass

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        return self.rest_accessor.query_history(req)

    def close(self) -> None:
        """关闭连接"""
        self.rest_accessor.stop()
        self.market_listener.stop()

    def on_order(self, order: OrderData) -> None:
        """推送委托数据"""
        self.orders[order.orderid] = copy(order)
        super().on_order(order)

    def on_position(self, position: PositionData) -> None:
        self.positions[position.ab_symbol] = copy(position)
        super().on_position(position)

    def get_order(self, orderid: str) -> OrderData:
        """查询委托数据"""
        return self.orders.get(orderid, None)

    def process_timer_event(self, event: Event) -> None:
        """定时事件处理,账户信息，订单信息回报用定时任务来处理"""
        self.count += 1
        if self.count < 10:
            return
        self.count = 0
        self.query_account()

    def init_query(self) -> None:
        """初始化查询任务"""
        self.count: int = 0
        self.event_dispatcher.register(
            EventType.EVENT_TIMER, self.process_timer_event)
