from typing import Dict, Iterable, List

from abquant.gateway.basegateway import Gateway
from abquant.trader.common import Exchange
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from abquant.trader.msg import BarData
from abquant.event import EventDispatcher

from .bybit_spot_listener import BybitSpotMarketWebsocketListener
from .bybit_spot_accessor import BybitSpotAccessor


class BybitSpotGateway(Gateway):
    default_setting: Dict[str, str] = {
        # "key": "",
        # "secret": "",
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["REAL", "TESTNET"],
    }

    exchanges = [Exchange.BYBIT]

    def __init__(self, event_dispatcher: EventDispatcher):
        """"""
        super().__init__(event_dispatcher, "BYBITS")
        
        self.rest_accessor = None
        self.market_listener = None
        
    def connect(self, setting: dict) -> None:
        """"""
        try:
            key = setting["key"]
            secret = setting["secret"]
        except LookupError as e:
            self.write_log("the setting not contain field 'key' and field 'secret', only for market data")

        server = setting.get("test_net", self.default_setting["test_net"][1])
        proxy_host = setting.get(
            "proxy_host", self.default_setting["proxy_host"])        
        proxy_port = setting.get(
            "proxy_port", self.default_setting["proxy_port"])

        self.rest_accessor = BybitSpotAccessor(self)
        self.rest_accessor.connect(
            key,
            secret,
            server,
            proxy_host,
            proxy_port
        )

        self.market_listener = BybitSpotMarketWebsocketListener(self)
        self.market_listener.connect(
            server,
            proxy_host,
            proxy_port
        )
        self.on_gateway(self)
        
    def start(self):
        self.market_listener.start()

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.market_listener.subscribe(req)

    def close(self) -> None:
        """关闭连接"""
        self.market_listener.stop()

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
        self.rest_accessor.query

    def query_position(self):
        pass

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        return self.rest_accessor.query_history(req)
