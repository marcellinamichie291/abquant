from abquant.event.dispatcher import EventDispatcher
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from abquant.gateway.basegateway import Gateway
from abquant.gateway.binances.binancesaccesser import BinanceAccessor
from abquant.trader.common import Exchange
from .binancelistener import BinanceSDataWebsocketListener, BinanceSTradeWebsocketListener
from abquant.event.event import EventType


class BinanceSGateway(Gateway):
    default_setting = {
        "key": "",
        "secret": "",
        "session_number": 3,
        "proxy_host": "",
        "proxy_port": 0,
    }

    exchanges = [Exchange.BINANCE]

    def __init__(self, event_dispatcher: EventDispatcher):
        super().__init__(event_dispatcher, "BINANCES")

        # self.market_listener =
        self.market_listener = BinanceSDataWebsocketListener(self)
        self.trade_listener = BinanceSTradeWebsocketListener(self)
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

        self.event_dispatcher.register(
            EventType.EVENT_TIMER, self.process_timer_event)

        self.on_gateway(self)

    def subscribe(self, req: SubscribeRequest):
        """"""
        self.market_listener.subscribe(req)

    def start(self):
        self.market_listener.start()

    def send_order(self, req: OrderRequest):
        """"""
        return self.rest_accessor.send_order(req)

    def cancel_order(self, req: CancelRequest):
        """"""
        self.rest_accessor.cancel_order(req)

    def cancel_orders(self, reqs):
        pass
        # return super(BinanceSGateway, self).cancel_orders(reqs)

    def query_account(self):
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

    def query_position(self):
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

    def query_history(self, req: HistoryRequest):
        """"""
        return self.rest_accessor.query_history(req)

    def close(self):
        """"""
        self.rest_accessor.stop()
        self.market_listener.stop()
        self.trade_listener.stop()

    def process_timer_event(self, event) -> None:
        """"""
        self.rest_accessor.keep_user_stream()


