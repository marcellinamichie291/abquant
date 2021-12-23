

from typing import Dict, List
from abquant.gateway import basegateway
from abquant.trader.common import Exchange
from abquant.trader.msg import BarData
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest

from bybit_accessor import BybitAccessor
from bybit_listener import BybitMarketWebsocketListener, BybitTradeWebsocketListener
from abquant.event import EventDispatcher


class BybitGateway(basegateway):
    """
    vn.py用于对接Bybit交易所的交易接口。
    """

    default_setting: Dict[str, str] = {
        "key": "",
        "secret": "",
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["REAL", "TESTNET"],
    }

    exchanges: List[Exchange] = [Exchange.BYBIT]

    def __init__(self, event_dispatcher: EventDispatcher):
        """构造函数"""
        super().__init__(event_dispatcher, "BYBIT")

        self.rest_api = None
        self.private_ws_api = None
        self.public_ws_api = None

    def connect(self, setting: dict) -> None:
        """连接交易接口"""
        self.rest_api = BybitAccessor(self)
        self.private_ws_api = BybitTradeWebsocketListener(self)
        self.public_ws_api = BybitMarketWebsocketListener(self)
        key: str = setting["key"]
        secret: str = setting["secret"]
        server: str = setting["test_net"]
        proxy_host: str = setting["proxy_host"]
        proxy_port: str = setting["proxy_port"]

        if proxy_port.isdigit():
            proxy_port = int(proxy_port)
        else:
            proxy_port = 0

        self.rest_api.connect(
            key,
            secret,
            server,
            proxy_host,
            proxy_port
        )
        self.private_ws_api.connect(
            key,
            secret,
            server,
            proxy_host,
            proxy_port
        )
        self.public_ws_api.connect(
            server,
            proxy_host,
            proxy_port
        )

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.public_ws_api.subscribe(req)

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        return self.rest_api.send_order(req)

    def cancel_order(self, req: CancelRequest):
        """委托撤单"""
        self.rest_api.cancel_order(req)

    def query_account(self) -> None:
        """查询资金"""
        pass

    def query_position(self) -> None:
        """查询持仓"""
        return

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        return self.rest_api.query_history(req)

    def close(self) -> None:
        """关闭连接"""
        if self.rest_api:
            self.rest_api.stop()
            self.private_ws_api.stop()
            self.public_ws_api.stop()
