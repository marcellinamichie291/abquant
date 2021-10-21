from abc import abstractmethod
from abquant.event.event import EventType
from abquant.gateway.accessor import Request
from abquant.event.dispatcher import Event
from typing import Iterable
from abquant.trader.msg import BarData
from abquant.trader.object import AccountData, CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest

from abquant.event import EventDispatcher
from abquant.trader.common import Exchange
from abquant.gateway.basegateway import Gateway

from dydx_listener import DydxWebsocketListener
from dydx_accessor import DydxAccessor

class DydxGateway(Gateway):
    default_setting = {
        "key": "",
        "secret": "",
        "passphrase": "",
        "stark_private_key": "",
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["TESTNET", "REAL"],
    }
    exchanges: Exchange = [Exchange.DYDX]

    def __init__(self, event_dispatcher: EventDispatcher):
        super().__init__(event_dispatcher, "DYDX")

        self.market_listener = DydxWebsocketListener(self)
        self.rest_accessor = DydxAccessor(self)