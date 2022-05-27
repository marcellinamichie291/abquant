from typing import Iterable, List
from abquant.trader.msg import BarData, OrderData
from abquant.trader.object import  CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from .raydium_listener import RaydiumWebsocketListener
from abquant.event import EventDispatcher
from abquant.trader.common import Exchange
from abquant.gateway.basegateway import Gateway


class RaydiumGateway(Gateway):

    default_setting = {
        "secret_key": "",
    }
    exchanges: Exchange = [Exchange.RAYDIUNM]

    def __init__(self, event_dispatcher: EventDispatcher, gateway_name: str = "RAYDIUM") -> None:
        """构造函数"""
        super().__init__(event_dispatcher, gateway_name)
        self.set_gateway_name(gateway_name)
        self.listener = RaydiumWebsocketListener(self)

    def connect(self, setting: dict) -> None:
        """"""
        # secret_key: str = setting["secret_key"]  #secret_key for access
        self.listener.connect()
        self.on_gateway(self)

    def start(self):
        self.listener.start()

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.listener.subscribe(req)

    def close(self) -> None:
        """关闭连接"""
        self.listener.stop()

    def send_order(self, req: OrderRequest) -> None:
        """委托下单"""
        pass

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        pass

    def cancel_orders(self, reqs: Iterable[CancelRequest]) -> None:
        pass

    def query_account(self) -> None:
        """查询资金"""
        pass

    def query_position(self) -> None:
        """查询持仓"""
        pass

    def query_orders(self) -> None:
        """查询未成交委托"""
        pass

    def on_order(self, order: OrderData) -> None:
        """推送委托数据"""
        pass

    def get_order(self, orderid: str) -> OrderData:
        """查询委托数据"""
        pass

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        pass

