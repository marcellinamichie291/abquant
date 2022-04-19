from copy import copy
from typing import Dict, Iterable, List
from abquant.trader.msg import BarData, OrderData
from abquant.trader.object import  CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from .ftx_accessor import FtxAccessor
from .ftx_listener import FtxWebsocketListener
from abquant.event import EventDispatcher
from abquant.trader.common import Exchange
from abquant.gateway.basegateway import Gateway

class FtxGateway(Gateway):

    default_setting = {
        "key": "",
        "secret": "",
        "proxy_host": "",
        "proxy_port": 0
    }
    exchanges: Exchange = [Exchange.FTX]

    def __init__(self, event_dispatcher: EventDispatcher, gateway_name: str = "FTX") -> None:
        """构造函数"""
        super().__init__(event_dispatcher, gateway_name)
        self.set_gateway_name(gateway_name)
        self.listener = FtxWebsocketListener(self)
        self.accessor = FtxAccessor(self)

        self.orders: Dict[str, OrderData] = {}
        self.order_id: Dict[str, str] = {}

    def connect(self, setting: dict) -> None:
        """连接交易接口"""
        key: str = setting["key"]
        secret: str = setting["secret"]
        proxy_host: str = setting["proxy_host"]
        proxy_port: int = setting["proxy_port"]

        self.accessor.connect(key, secret, proxy_host, proxy_port)
        self.listener.connect(key, secret, proxy_host, proxy_port)

        self.on_gateway(self)
        
    def start(self):
        self.listener.start()
        
    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.listener.subscribe(req)

    def send_order(self, req: OrderRequest) -> None:
        """委托下单"""
        return self.accessor.send_order(req)

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        self.accessor.cancel_order(req)
        
    def cancel_orders(self, reqs: Iterable[CancelRequest]) -> None:
        return super().cancel_orders(reqs)
    
    def query_account(self) -> None:
        """查询资金"""
        self.accessor.query_account()

    def query_position(self) -> None:
        """查询持仓"""
        self.accessor.query_position()

    def query_orders(self) -> None:
        """查询未成交委托"""
        self.accessor.query_order()

    def on_order(self, order: OrderData) -> None:
        """推送委托数据"""
        self.orders[order.orderid] = copy(order)
        super().on_order(order)

    def get_order(self, orderid: str) -> OrderData:
        """查询委托数据"""
        return self.orders.get(orderid, None)

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        return self.accessor.query_history(req)

    def close(self) -> None:
        """关闭连接"""
        self.accessor.stop()
        self.listener.stop()


