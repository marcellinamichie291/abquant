from abc import abstractmethod
from abquant.event.event import EventType
from abquant.gateway.accessor import Request
from abquant.event.dispatcher import Event
from typing import Iterable
from abquant.trader.msg import BarData
from abquant.trader.object import AccountData, CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from .binancecaccessor import BinanceCAccessor
from .binanceclistener import BinanceCDataWebsocketListener, BinanceCTradeWebsocketListener
from abquant.event import EventDispatcher
from abquant.trader.common import Exchange
from abquant.gateway.basegateway import Gateway


class BinanceCGateway(Gateway):
    default_setting = {
        "key": "",
        "secret": "",
        "session_number": 3,
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["TESTNET", "REAL"],
        "position_mode":["One-way", "Hedge"][0],
    }
    exchanges = [Exchange.BINANCE]

    # self.market_listener =
    def __init__(self, event_dispatcher: EventDispatcher):
        """Constructor"""
        # attention! call the set_gateway_name in the derived class.
        super().__init__(event_dispatcher, "BINANCEC")

        self.market_listener = BinanceCDataWebsocketListener(self)
        self.trade_listener = BinanceCTradeWebsocketListener(self)
        self.rest_accessor = BinanceCAccessor(self)

    @abstractmethod
    def ustd_based(self) -> bool:
        raise NotImplementedError(
            " this class {} is not for trader use. Use BinanceUBCGateway or BinanceBBCGateway instead".format(self.__class__.__name__))

    def connect(self, setting: dict) -> None:
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
        proxy_port = setting.get(
            "proxy_port", self.default_setting["proxy_port"])
        
        position_mode = setting.get("position_mode", self.default_setting["position_mode"])


        self.rest_accessor.connect(self.ustd_based(), key, secret, position_mode, session_number, server,
                                   proxy_host, proxy_port)
        self.market_listener.connect(
            self.ustd_based(), proxy_host, proxy_port, server)

        self.event_dispatcher.register(
            EventType.EVENT_TIMER, self.process_timer_event)
        self.on_gateway(self)

    def subscribe(self, req: SubscribeRequest) -> None:
        """"""
        self.market_listener.subscribe(req)

    def start(self):
        self.market_listener.start()

    def send_order(self, req: OrderRequest) -> str:
        """"""
        super(BinanceCGateway, self).send_order(req)
        return self.rest_accessor.send_order(req)

    def cancel_order(self, req: CancelRequest) -> Request:
        """"""
        self.rest_accessor.cancel_order(req)

    def cancel_orders(self, reqs: Iterable[CancelRequest]) -> None:
        return super().cancel_orders(reqs)

    def query_account(self) -> Iterable[AccountData]:
        """"""
        raise NotImplementedError(
            "do not use this method. Use ordermanager to get the updated account information instead.")
        accounts = self.trade_listener.accounts
        if accounts is not None:
            return accounts
        accounts = self.rest_accessor.accounts
        if accounts is None:
            raise LookupError(
                "please call the conect method of gateway first and block for a while due to the reason of the async io")
        return accounts

    def query_position(self) -> Iterable[AccountData]:
        """"""
        raise NotImplementedError(
            "do not use this method. Use ordermanager to get the updated position information instead.")
        positions = self.trade_listener.positions
        if positions is not None:
            return positions
        positions = self.rest_accessor.positions
        if positions is None:
            raise LookupError(
                "please call the conect method of gateway first and block for a while due to the reason of the async io")
        return positions

    def query_history(self, req: HistoryRequest) -> Iterable[BarData]:
        """"""
        return self.rest_accessor.query_history(req)

    def close(self) -> None:
        """"""
        self.rest_accessor.stop()
        self.trade_listener.stop()
        self.market_listener.stop()

    def process_timer_event(self, event: Event) -> None:
        """"""
        self.rest_accessor.keep_user_stream(event.data)
        self.rest_accessor.reset_server_time(event.data)


