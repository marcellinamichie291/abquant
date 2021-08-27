from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from .. import Gateway
from . import BinanceAccessor
from abquant.trader.common import Exchange
from abquant.event import EventType

class BinanceSGateway(Gateway):

    default_setting = {
        "key": "",
        "secret": "",
        "session_number": 3,
        "proxy_host": "",
        "proxy_port": 0,
    }

    exchanges = [Exchange.BINANCE]

    def __init__(self, event_engine):
        super().__init__(event_engine, "BINANCE")

        # self.market_listener =
        self.rest_accessor = BinanceAccessor(self)

    def connect(self, setting: dict):
        """"""
        key = setting["key"]
        secret = setting["secret"]
        session_number = setting["session_number"]
        proxy_host = setting["proxy_host"]
        proxy_port = setting["proxy_port"]

        self.rest_accessor.connect(key, secret, session_number,
                              proxy_host, proxy_port)
        self.market_listener.connect(proxy_host, proxy_port)


    def subscribe(self, req: SubscribeRequest):
        """"""
        self.market_listener.subscribe(req)

    def send_order(self, req: OrderRequest):
        """"""
        return self.rest_accessor.send_order(req)

    def cancel_order(self, req: CancelRequest):
        """"""
        self.rest_accessor.cancel_order(req)

    def query_account(self):
        """"""
        pass

    def query_position(self):
        """"""
        pass

    def query_history(self, req: HistoryRequest):
        """"""
        return self.rest_accessor.query_history(req)

    def close(self):
        """"""
        self.rest_accessor.stop()
        self.market_listener.stop()

