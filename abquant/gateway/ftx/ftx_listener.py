
import hmac
import time
from datetime import datetime
from typing import Dict, List
from copy import copy

from . import DIRECTION_FTX2AB, ORDERTYPE_FTX2AB, WEBSOCKET_HOST, symbol_contract_map, change_datetime, generate_datetime, local_orderids
from ..basegateway import Gateway
from ..listener import WebsocketListener
from abquant.trader.common import Direction, Exchange, OrderType, Status
from abquant.trader.object import  SubscribeRequest
from abquant.trader.msg import DepthData, OrderData, TickData, TradeData, TransactionData


class FtxWebsocketListener(WebsocketListener):
    """"""

    def __init__(self, gateway: Gateway) -> None:
        """"""
        super(FtxWebsocketListener, self).__init__(gateway)

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

        self.authenticate(self.api_key, self.api_secret_key)

        for req in list(self.subscribed.values()):
            self.subscribe(req)
            
        self.subscribe_private_channels()

    def on_disconnected(self) -> None:
        """"""
        self.gateway.write_log("Websocket 连接断开")

    def authenticate(
        self,
        api_key: str,
        api_secret_key: str
    ) -> None:
        """"""
        timestamp: int = int(time.time() * 1000)
        signature_payload = f'{timestamp}websocket_login'.encode()
        signature: str = hmac.new(api_secret_key.encode(), signature_payload, 'sha256').hexdigest()
        auth = {
            'args': {
                'key': api_key,
                'sign': signature,
                'time': timestamp
                },
            'op': 'login'
        }
        self.send_packet(auth)

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
        tick, depth, transaction, _ = self.make_data(symbol, Exchange.FTX, datetime.now(), self.gateway_name)
        self.ticks[symbol] = tick
        self.transactions[symbol] = transaction
        self.depths[symbol] = depth
        subscribe_mode = self.gateway.subscribe_mode
        if subscribe_mode.best_tick:
            subscribe_ticker = {'op': 'subscribe', 'channel': 'ticker', 'market': symbol}
            self.send_packet(subscribe_ticker)
            
        if subscribe_mode.tick_5 or subscribe_mode.depth:
            subscribe_orderbook = {'op': 'subscribe', 'channel': 'orderbook', 'market': symbol}
            self.send_packet(subscribe_orderbook)
            
        if subscribe_mode.transaction:
            subscribe_trade = {'op': 'subscribe', 'channel': 'trades', 'market': symbol}
            self.send_packet(subscribe_trade)

    def subscribe_private_channels(self) -> None:
        """成交 订单回报"""
        self.send_packet({'op': 'subscribe', 'channel': 'fills'})
        self.send_packet({'op': 'subscribe', 'channel': 'orders'})

    def on_packet(self, packet) -> None:
        """"""
        if packet["type"] == "update":
            channel = packet["channel"]

            if channel == "ticker":
                symbol = packet["market"]
                data = packet["data"]
                tick = self.ticks[symbol]
                
                tick.trade_price = data["last"]
                tick.trade_volume = 0

                tick.best_ask_price = data['ask']
                tick.best_ask_volume = data['askSize']
                tick.best_bid_price = data['bid']
                tick.best_bid_volume = data['bidSize']
                tick.localtime = datetime.now()

                self.gateway.on_tick(copy(tick))
                
            elif channel == "orderbook":
                symbol = packet["market"]
                orderbook = self.orderbook[symbol].add(packet["data"]["bids"], packet["data"]["asks"])
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
                    tick.datetime = generate_datetime(packet["data"]["time"]),
                    tick.localtime = datetime.now()
                    self.gateway.on_tick(copy(tick))
                    
                if self.gateway.subscribe_mode.depth:
                    depth = self.depths[symbol]
                    for p, v in packet["data"]["bids"]:
                        depth.volume = v
                        depth.price = p
                        depth.direction = Direction.LONG
                        self.gateway.on_depth(copy(depth))
                    for p, v in packet["data"]["asks"]:
                        depth.volume = v
                        depth.price = p
                        depth.direction = Direction.SHORT
                        self.gateway.on_depth(copy(depth))                        
                        
            elif channel == "trades":
                symbol: str = packet["market"]
                trade_data = packet["data"]
                for data in trade_data:
                    transaction: TradeData = self.transactions[symbol]
                    tick: TickData = self.ticks[symbol]
                    dt = change_datetime(data["time"])
                    dt_now = datetime.now()
                    p = data["price"]
                    v = data["size"]
                    
                    tick.trade_price = p
                    tick.trade_volume = v
                    tick.datetime = dt
                    tick.localtime = dt_now
                    
                    transaction.datetime = dt
                    transaction.volume = v
                    transaction.price = p
                    transaction.direction = DIRECTION_FTX2AB[data["side"]]
                    
                    self.gateway.on_tick(copy(tick))
                    self.gateway.on_transaction(copy(transaction))

            elif channel == "fills":
                d = packet["data"]
                trade: TradeData = TradeData(
                    symbol=d["market"],
                    exchange=Exchange.FTX,
                    orderid=local_orderids.add(d["orderId"]),
                    tradeid=d["tradeId"],
                    direction=DIRECTION_FTX2AB[d["side"]],
                    price=d["price"],
                    volume=d["size"],
                    datetime=change_datetime(d["time"]),
                    gateway_name=self.gateway_name,
                )
                self.gateway.on_trade(trade)
                
                # TODO: websocket 没有仓位账户回报 调用rest api
                self.gateway.query_position()
                self.gateway.query_account()

            elif channel == "orders":
                d = packet["data"]
                current_status = d["status"]
                size = d["size"]
                filled_size = d["filledSize"]
                remaining_size = d["remainingSize"]
                if current_status == "new":
                    status = Status.NOTTRADED
                elif (current_status == "open") & (filled_size == 0):
                    status = Status.NOTTRADED
                elif (current_status == "open") & (size != filled_size):
                    status = Status.PARTTRADED
                elif (current_status == "closed") & ((size != filled_size)):
                    status = Status.CANCELLED
                elif (remaining_size == 0) & (size == filled_size):
                    status = Status.ALLTRADED
                else:
                    status = "other status"

                order: OrderData = OrderData(
                    orderid=d["clientId"],
                    symbol=d["market"],
                    exchange=Exchange.FTX,
                    price=d["price"],
                    volume=d["size"],
                    type=ORDERTYPE_FTX2AB[d["type"]],
                    direction=DIRECTION_FTX2AB[d["side"]],
                    traded=d["filledSize"],
                    status=status,
                    datetime=change_datetime(d["createdAt"]),
                    gateway_name=self.gateway_name,
                )
                local_orderids.add(d["clientId"])
                self.gateway.on_order(order)

            else:
                pass

        elif packet["type"] == "partial":
            # 订单簿快照
            channel = packet["channel"]
            if channel == "orderbook":
                symbol = packet['market']
                self.orderbook[symbol] = OrderBook()
                orderbook = self.orderbook[symbol].init(packet["data"]["bids"], packet["data"]["asks"])
                tick = self.ticks[symbol]

                for i in range(5):
                    n = i + 1
                    setattr(tick, f"bid_price_{n}", orderbook["bid"][i][0])
                    setattr(tick, f"bid_volume_{n}", orderbook["bid"][i][1])
                    setattr(tick, f"ask_price_{n}", orderbook["ask"][i][0])
                    setattr(tick, f"ask_volume_{n}", orderbook["ask"][i][1])
                
                tick.trade_price = 0
                tick.trade_volume = 0
                
                tick.datetime = generate_datetime(packet["data"]["time"]),
                tick.localtime = datetime.now()
                self.gateway.on_tick(copy(tick))

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
            p.append([self.bids[i], self.bid_dict[self.bids[i]]])
            q.append([self.asks[i], self.ask_dict[self.asks[i]]])

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