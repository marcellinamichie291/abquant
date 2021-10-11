from abc import abstractmethod
from abquant.event.event import EventType
from abquant.gateway.accessor import Request
from abquant.event.dispatcher import Event
from typing import Iterable
from abquant.trader.msg import BarData
from abquant.trader.object import AccountData, CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from .bitmexaccessor import BitmexAccessor
from .bitmexlistener import BitmexListener
from abquant.event import EventDispatcher
from abquant.trader.common import Exchange
from abquant.gateway.basegateway import Gateway


from ..basegateway import Gateway


class BitmexGateway(Gateway):
    default_setting = {
        "key": "",
        "secret": "",
        "session_number": 3,
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["TESTNET", "REAL"],
    }

    exchanges = [Exchange.BITMEX]

    def __init__(self, event_dispatcher: EventDispatcher):
        """Constructor"""
        super(BitmexGateway, self).__init__(event_dispatcher, "BITMEX")

        self.trade_accessor = BitmexAccessor(self)
        self.market_listener = BitmexListener(self)

        event_dispatcher.register(
            EventType.EVENT_TIMER, self.process_timer_event)

    def connect(self, setting: dict):
        """"""
        try:
            key = setting["key"]
            secret = setting["secret"]
        except LookupError as e:
            raise LookupError(
                "the setting must contain field 'key' and field 'secret'.")
        session_number = setting.get(
            "session_number", self.default_setting["session_number"])
        server = setting.get("test_net", self.default_setting["test_net"][1])
        proxy_host = setting.get(
            "proxy_host", self.default_setting["proxy_host"])
        proxy_port = int(setting.get(
            "proxy_port", self.default_setting["proxy_port"]))

        self.trade_accessor.connect(key, secret, session_number,
                                    server, proxy_host, proxy_port)

        # will push all account status on connected, including asset, position and orders while connecting.
        self.market_listener.connect(key, secret, server,
                                     proxy_host, proxy_port)
        self.on_gateway(self)

    def start(self):
        self.market_listener.start()

    def subscribe(self, req: SubscribeRequest):
        """"""
        self.market_listener.subscribe(req)

    def send_order(self, req: OrderRequest):
        """"""
        return self.trade_accessor.send_order(req)

    def cancel_order(self, req: CancelRequest):
        """"""
        self.trade_accessor.cancel_order(req)

    def query_account(self):
        """"""
        raise DeprecationWarning(" not do supprt this api anymore")

    def query_position(self):
        """"""
        raise DeprecationWarning(" not do supprt this api anymore")

    def query_history(self, req: HistoryRequest):
        """"""
        return self.trade_accessor.query_history(req)

    def close(self):
        """"""
        self.trade_accessor.stop()
        self.market_listener.stop()

    def process_timer_event(self, event: Event):
        """"""
        self.trade_accessor.reset_rate_limit()
