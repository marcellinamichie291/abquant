from typing import Dict, Iterable, List

from abquant.gateway.basegateway import Gateway
from abquant.trader.common import Exchange
from abquant.trader.object import SubscribeRequest
from abquant.event import EventDispatcher

from .bybit_spot_listener import BybitSpotMarketWebsocketListener


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
        
        self.market_listener = None
        
    def connect(self, setting: dict) -> None:
        """"""

        server = setting.get("test_net", self.default_setting["test_net"][1])
        proxy_host = setting.get(
            "proxy_host", self.default_setting["proxy_host"])        
        proxy_port = setting.get(
            "proxy_port", self.default_setting["proxy_port"])

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
            