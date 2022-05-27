import hmac
import time
from datetime import datetime
from typing import Dict, List
from copy import copy

from . import DIRECTION_GATE2AB, WEBSOCKET_HOST, symbol_contract_map, change_datetime, \
    generate_datetime, local_orderids
from ..basegateway import Gateway
from ..listener import WebsocketListener
from abquant.trader.common import Direction, Exchange, OrderType, Status
from abquant.trader.object import SubscribeRequest
from abquant.trader.msg import DepthData, OrderData, TickData, TradeData, TransactionData


class GateWebsocketListener(WebsocketListener):
    """"""

    def __init__(self, gateway: Gateway) -> None:
        """"""
        super(GateWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 10

        self.ticks: Dict[str, TickData] = {}
        self.transactions: Dict[str, TransactionData] = {}
        self.depths: Dict[str, DepthData] = {}

        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.orderbook: Dict[str, OrderBook] = {}

    def connect(
            self,
            api_key: str,
            api_secret_key: str,
            proxy_host: str,
            proxy_port: int
    ) -> None:
        """连接Websocket交易频道"""
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

        self.init(WEBSOCKET_HOST, self.proxy_host, self.proxy_port)

    def on_connected(self) -> None:
        """连接成功回报"""
        self.gateway.write_log("Websocket 连接成功")

        for req in list(self.subscribed.values()):
            self.subscribe(req)

    def on_disconnected(self) -> None:
        """"""
        self.gateway.write_log("Websocket 连接断开")

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅"""
        if req.symbol not in symbol_contract_map:
            self.gateway.write_log(f"找不到该合约代码{req.symbol}")
            return
        # if req.ab_symbol in self.subscribed:
        #     self.gateway.write_log(f"重复订阅{req.symbol}")
        #     return
        self.subscribed[req.ab_symbol] = req
        symbol = req.symbol
        name = req.name
        tick, depth, transaction, _ = self.make_data(symbol, Exchange.GATEIO, datetime.now(), self.gateway_name)
        self.ticks[symbol] = tick
        self.transactions[symbol] = transaction
        self.depths[symbol] = depth
        subscribe_mode = self.gateway.subscribe_mode
        if subscribe_mode.best_tick:
            subscribe_ticker = {
                "time": int(time.time()),
                "channel": "spot.book_ticker",
                "event": "subscribe",  # "unsubscribe" for unsubscription
                "payload": [name]
            }
            self.send_packet(subscribe_ticker)

        if subscribe_mode.tick_5 or subscribe_mode.depth:
            subscribe_orderbook = {
                "time": int(time.time()),
                "channel": "spot.order_book",
                "event": "subscribe",  # "unsubscribe" for unsubscription
                "payload": [name, "5", "100ms"]
            }
            self.send_packet(subscribe_orderbook)

        if subscribe_mode.transaction:
            subscribe_trade = {
                "time": int(time.time()),
                "channel": "spot.trades",
                "event": "subscribe",  # "unsubscribe" for unsubscription
                "payload": [name]
            }
            self.send_packet(subscribe_trade)

    def on_packet(self, packet) -> None:
        """"""
        if packet["event"] == "update":
            channel = packet["channel"]

            if channel == "spot.book_ticker":

                data = packet["result"]
                symbol = data['s'].lower().replace('_','')
                tick = self.ticks[symbol]

                tick.trade_price = 0
                tick.trade_volume = 0

                tick.best_ask_price = float(data['a'])
                tick.best_ask_volume = float(data['A'])
                tick.best_bid_price = float(data['b'])
                tick.best_bid_volume = float(data['B'])
                tick.datetime = generate_datetime(data["t"]/1000)
                tick.localtime = datetime.now()

                self.gateway.on_tick(copy(tick))

            elif channel == "spot.order_book":
                data = packet["result"]
                symbol = data['s'].lower().replace('_','')
                self.orderbook[symbol] = OrderBook()
                orderbook = self.orderbook[symbol].init(data["bids"], data["asks"])
                if self.gateway.subscribe_mode.tick_5:
                    tick = self.ticks[symbol]
                    for i in range(5):
                        n = i + 1
                        setattr(tick, f"bid_price_{n}", orderbook["bid"][i][0])
                        setattr(tick, f"bid_volume_{n}", orderbook["bid"][i][1])
                        setattr(tick, f"ask_price_{n}", orderbook["ask"][i][0])
                        setattr(tick, f"ask_volume_{n}", orderbook["ask"][i][1])

                    tick.trade_price = 0
                    tick.trade_volume = 0
                    tick.datetime = generate_datetime(data["t"]/1000)
                    tick.localtime = datetime.now()

                    self.gateway.on_tick(copy(tick))

                if self.gateway.subscribe_mode.depth:
                    depth = self.depths[symbol]
                    for p, v in data["bids"]:
                        depth.volume = v
                        depth.price = p
                        self.gateway.on_depth(copy(depth))
                    for p, v in data["asks"]:
                        depth.volume = v
                        depth.price = p
                        self.gateway.on_depth(copy(depth))

            elif channel == "spot.trades":
                trade_data = packet["result"]
                symbol = trade_data['currency_pair'].lower().replace('_','')

                transaction: TradeData = self.transactions[symbol]
                tick: TickData = self.ticks[symbol]
                dt = generate_datetime((trade_data["create_time"]/1000))
                dt_now = datetime.now()
                p = float(trade_data["price"])
                v = float(trade_data["amount"])

                tick.trade_price = p
                tick.trade_volume = v
                tick.datetime = dt
                tick.localtime = dt_now

                transaction.datetime = dt
                transaction.volume = v
                transaction.price = p
                transaction.direction = DIRECTION_GATE2AB[trade_data["side"]]

                self.gateway.on_tick(copy(tick))
                self.gateway.on_transaction(copy(transaction))

            # elif channel == "fills":
            #     d = packet["data"]
            #     trade: TradeData = TradeData(
            #         symbol=d["market"],
            #         exchange=Exchange.FTX,
            #         orderid=local_orderids.add(d["orderId"]),
            #         tradeid=d["tradeId"],
            #         direction=DIRECTION_FTX2AB[d["side"]],
            #         price=d["price"],
            #         volume=d["size"],
            #         datetime=change_datetime(d["time"]),
            #         gateway_name=self.gateway_name,
            #     )
            #     self.gateway.on_trade(trade)
            #
            #     # TODO: websocket 没有仓位账户回报 调用rest api
            #     self.gateway.query_position()
            #     self.gateway.query_account()
            #
            # elif channel == "orders":
            #     d = packet["data"]
            #     current_status = d["status"]
            #     size = d["size"]
            #     filled_size = d["filledSize"]
            #     remaining_size = d["remainingSize"]
            #     if current_status == "new":
            #         status = Status.NOTTRADED
            #     elif (current_status == "open") & (filled_size == 0):
            #         status = Status.NOTTRADED
            #     elif (current_status == "open") & (size != filled_size):
            #         status = Status.PARTTRADED
            #     elif (current_status == "closed") & ((size != filled_size)):
            #         status = Status.CANCELLED
            #     elif (remaining_size == 0) & (size == filled_size):
            #         status = Status.ALLTRADED
            #     else:
            #         status = "other status"
            #
            #     order: OrderData = OrderData(
            #         orderid=d["clientId"],
            #         symbol=d["market"],
            #         exchange=Exchange.FTX,
            #         price=d["price"],
            #         volume=d["size"],
            #         type=ORDERTYPE_FTX2AB[d["type"]],
            #         direction=DIRECTION_FTX2AB[d["side"]],
            #         traded=d["filledSize"],
            #         status=status,
            #         datetime=change_datetime(d["createdAt"]),
            #         gateway_name=self.gateway_name,
            #     )
            #     local_orderids.add(d["clientId"])
            #     self.gateway.on_order(order)

            else:
                pass

        else:
            pass


class OrderBook:
    """重建订单簿"""

    def __init__(self):
        """"""
        self.bids = []
        self.asks = []
        self.bid_dict = {}
        self.ask_dict = {}

    def init(self, bid: List[List], ask: List[List]) -> List[List]:
        """"""
        for i in bid:
            self.bids.append(float(i[0]))
            self.bid_dict[i[0]] = float(i[1])
        self.bids.sort(reverse=True)

        for i in ask:
            self.asks.append(float(i[0]))
            self.ask_dict[i[0]] = float(i[1])
        self.asks.sort(reverse=False)

        p: List[List] = []
        q: List[List] = []
        for i in range(5):
            p.append([self.bids[i], self.bid_dict.get(self.bids[i])])
            q.append([self.asks[i], self.ask_dict.get(self.asks[i])])

        return {"bid": p, "ask": q}

    def bid_add(self, bid: List[List]) -> None:
        """"""
        if len(bid) > 0:
            for i in bid:
                if float(i[1]) == 0:
                    if float(i[0]) in self.bids:
                        self.bids.remove(float(i[0]))
                        self.bid_dict.pop(float(i[0]))
                else:
                    if float(i[0]) not in self.bids:
                        self.bids.append(float(i[0]))
                    self.bid_dict[float(i[0])] = float(i[1])
            self.bids.sort(reverse=True)

    def ask_add(self, ask: List[List]) -> None:
        """"""
        if len(ask) > 0:
            for i in ask:
                if float(i[1]) == 0:
                    if float(i[0]) in self.asks:
                        self.asks.remove(float(i[0]))
                        self.ask_dict.pop(float(i[0]))
                else:
                    if float(i[0]) not in self.asks:
                        self.asks.append(float(i[0]))
                    self.ask_dict[float(i[0])] = float(i[1])
            self.asks.sort(reverse=False)

    def add(self, bid: List[List], ask: List[List]) -> List[List]:
        """"""
        self.bid_add(bid)
        self.ask_add(ask)

        p: List[List] = []
        q: List[List] = []
        for i in range(5):
            p.append([self.bids[i], self.bid_dict[self.bids[i]]])
            q.append([self.asks[i], self.ask_dict[self.asks[i]]])

        return {"bid": p, "ask": q}
