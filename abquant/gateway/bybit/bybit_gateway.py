from typing import Dict, Iterable, List

from abquant.gateway.basegateway import Gateway
from abquant.trader.common import Exchange
from abquant.trader.msg import BarData
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from abquant.event import EventDispatcher

from .bybit_accessor import BybitAccessor
from .bybit_listener import BybitMarketWebsocketListener, BybitTradeWebsocketListener


class BybitGateway(Gateway):
    default_setting: Dict[str, str] = {
        "key": "",
        "secret": "",
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["REAL", "TESTNET"],
    }

    exchanges = [Exchange.BYBIT]

    def __init__(self, event_dispatcher: EventDispatcher, gateway_name="BYBIT"):
        """"""
        super().__init__(event_dispatcher, gateway_name)
        
        self.set_gateway_name(gateway_name)
        self.rest_accessor = BybitAccessor(self)
        self.trade_listener = BybitTradeWebsocketListener(self)
        self.market_listener = BybitMarketWebsocketListener(self)
        
    def connect(self, setting: dict) -> None:
        """"""

        try:
            key = setting["key"]
            secret = setting["secret"]
        except LookupError as e:
            raise LookupError(
                "the setting must contain field 'key' and field 'secret'.")
            
        server = setting.get("test_net", self.default_setting["test_net"][1])
        proxy_host = setting.get(
            "proxy_host", self.default_setting["proxy_host"])        
        proxy_port = setting.get(
            "proxy_port", self.default_setting["proxy_port"])

        self.rest_accessor.connect(
            key,
            secret,
            server,
            proxy_host,
            proxy_port
        )
        self.trade_listener.connect(
            key,
            secret,
            server,
            proxy_host,
            proxy_port
        )
        self.market_listener.connect(
            server,
            proxy_host,
            proxy_port
        )
        self.on_gateway(self)
        
    def start(self):
        self.market_listener.start()
        self.trade_listener.start()

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.market_listener.subscribe(req)

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        return self.rest_accessor.send_order(req)

    def cancel_orders(self, reqs: Iterable[CancelRequest]) -> None:
        return super().cancel_orders(reqs)
    
    def cancel_order(self, req: CancelRequest):
        """委托撤单"""
        self.rest_accessor.cancel_order(req)

    def query_account(self) -> None:
        """查询资金"""
        pass

    def query_position(self) -> None:
        """查询持仓"""
        return

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        return self.rest_accessor.query_history(req)

    def close(self) -> None:
        """关闭连接"""
        if self.rest_accessor:
            self.rest_accessor.stop()
            self.trade_listener.stop()
            self.market_listener.stop()
