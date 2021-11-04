from typing import Dict, List
from datetime import datetime
from copy import copy
from . import (
    DIRECTION_DYDX2AB, 
    WEBSOCKET_HOST, 
    TESTNET_WEBSOCKET_HOST, 
    STATUS_DYDX2AB,
    ORDERTYPE_DYDX2AB, 
    symbol_contract_map, 
)

from ..listener import WebsocketListener
from .dydx_getway import Gateway
from ...trader.object import (
    OrderData, 
    HistoryRequest, 
    SubscribeRequest,
    HistoryRequest,
    Status,
    Direction
)
from ...trader.msg import BarData, TickData, TradeData, DepthData
from ...trader.common import Exchange, Interval

from .dydx_util import generate_datetime, api_key_credentials_map, generate_datetime_iso, sign, generate_now_iso, UTC_TZ

class DydxWebsocketListener(WebsocketListener):
    """
    dydx websocket
    """
    def __init__(self, gateway: Gateway):
        super(DydxWebsocketListener,self).__init__(gateway)
        self.ping_interval = 30
        self.gateway = gateway
        self.gateway.set_gateway_name(gateway.gateway_name)

        self.subscribed: Dict[str, SubscribeRequest] = {}
        self.orderbooks: Dict[str, "OrderBook"] = {}

    def connect(self, proxy_host, proxy_port, server, accountNumber):
        """"""
        self.accountNumber = accountNumber

        if server == "REAL":
            self.init(WEBSOCKET_HOST, proxy_host, proxy_port)
        else:
            self.init(TESTNET_WEBSOCKET_HOST, proxy_host, proxy_port)
        
        self.start()

    def on_connected(self):
        """"""
        self.gateway.write_log("Websocket API连接成功")
        self.subscribe_topic()

        for req in list(self.subscribed.values()):
            self.subscribe(req)
    
    def on_disconnected(self):
        self.gateway.write_log("Websocket API断开")

    def subscribe_topic(self) -> None:
        """订阅委托、资金和持仓推送"""
        now_iso_string = generate_now_iso()
        signature: str = sign(
            request_path="/ws/accounts",
            method="GET",
            iso_timestamp=now_iso_string,
            data={},
        )
        req: dict = {
            "type": "subscribe",
            "channel": "v3_accounts",
            "accountNumber": self.accountNumber,
            "apiKey": api_key_credentials_map["key"],
            "signature": signature,
            "timestamp": now_iso_string,
            "passphrase": api_key_credentials_map["passphrase"]
        }
        self.send_packet(req)

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        if req.symbol not in symbol_contract_map:
            self.gateway.write_log(f"找不到该合约代码{req.symbol}")
            return

        # 缓存订阅记录
        self.subscribed[req.ab_symbol] = req
        symbol = req.symbol

        orderbook = OrderBook(symbol, req.exchange, self.gateway)
        self.orderbooks[symbol] = orderbook
        # 开启批量数据订阅，与web版一致
        req: dict = {
            "type": "subscribe",
            "channel": "v3_orderbook",
            "id": symbol,
            "batched": True
        }
        self.send_packet(req)

        history_req: HistoryRequest = HistoryRequest(
            symbol=symbol,
            exchange=Exchange.DYDX,
            start=None,
            end=None,
            interval=Interval.DAILY
        )

        history: List[BarData] = self.gateway.query_history(history_req)

        orderbook.open_price = history[0].open_price
        orderbook.high_price = history[0].high_price
        orderbook.low_price = history[0].low_price
        orderbook.last_price = history[0].close_price

        req: dict = {
            "type": "subscribe",
            "channel": "v3_trades",
            "id": symbol
        }
        self.send_packet(req)

        
        # req: dict = {
        #     "type": "subscribe",
        #     "channel": "v3_markets"
        # }
        # self.send_packet(req)

    def on_packet(self, packet: dict) -> None:
        """推送数据回报"""
        type = packet.get("type", None)
        if type == "error":
            msg: str = packet["message"]
            self.gateway.write_log(msg)
            return

        channel: str = packet.get("channel", None)

        if channel:
            if packet["channel"] == "v3_orderbook" or packet["channel"] == "v3_trades":
                self.on_orderbook(packet)
            elif packet["channel"] == "v3_accounts":
                self.on_message(packet)

    def on_orderbook(self, packet: dict) -> None:
        """订单簿更新专用"""
        # id: BTC-USD
        # print("######on_orderbook",packet)
        orderbook = self.orderbooks[packet["id"]]
        orderbook.on_message(packet)

    def on_message(self, packet: dict) -> None:
        """Websocket账户更新推送"""
        for order_data in packet["contents"]["orders"]:
            # 绑定本地和系统委托号映射
            self.gateway.local_sys_map[order_data["clientId"]] = order_data["id"]
            self.gateway.sys_local_map[order_data["id"]] = order_data["clientId"]
            order: OrderData = OrderData(
                symbol=order_data["market"],
                exchange=Exchange.DYDX,
                orderid=order_data["clientId"],
                type=ORDERTYPE_DYDX2AB[order_data["type"]],
                direction=DIRECTION_DYDX2AB[order_data["side"]],
                # offset=Offset.NONE,
                price=float(order_data["price"]),
                volume=float(order_data["size"]),
                traded=float(order_data["size"]) - float(order_data["remainingSize"]),
                status=STATUS_DYDX2AB.get(order_data["status"], Status.SUBMITTING),
                datetime=generate_datetime(order_data["createdAt"]),
                gateway_name=self.gateway_name
            )
            if 0 < order.traded < order.volume:
                order.status = Status.PARTTRADED
            self.gateway.on_order(order)

        if packet["type"] == "subscribed":
            self.gateway.posid = packet["contents"]["account"]["positionId"]
            self.gateway.id = packet["id"]
            self.gateway.init_query()
            self.gateway.write_log("账户资金查询成功")

        else:
            fills = packet["contents"].get("fills", None)
            if not fills:
                return

            for fill_data in packet["contents"]["fills"]:
                orderid: str = self.gateway.sys_local_map[fill_data["orderId"]]

                trade: TradeData = TradeData(
                    symbol=fill_data["market"],
                    exchange=Exchange.DYDX,
                    orderid=orderid,
                    tradeid=fill_data["id"],
                    direction=DIRECTION_DYDX2AB[fill_data["side"]],
                    price=float(fill_data["price"]),
                    volume=float(fill_data["size"]),
                    datetime=generate_datetime(fill_data["createdAt"]),
                    gateway_name=self.gateway_name
                )
                self.gateway.on_trade(trade)


class OrderBook():
    """储存dYdX订单簿数据"""

    def __init__(self, symbol: str, exchange: Exchange, gateway: Gateway) -> None:
        """构造函数"""

        self.asks = dict()
        self.bids = dict()
        self.gateway = gateway

        # 创建TICK对象
        self.tick: TickData = TickData(
            symbol=symbol,
            exchange=exchange,
            # name=symbol_contract_map[symbol].name,
            datetime=datetime.now(UTC_TZ),
            gateway_name=gateway.gateway_name,
        )

        # 创建DEPTH
        self.depth: DepthData = DepthData(
            symbol=symbol,
            exchange=exchange,
            datetime=datetime.now(UTC_TZ),
            gateway_name=gateway.gateway_name,
        )

        self.offset: int = 0
        self.open_price: float = 0.0
        self.high_price: float = 0.0
        self.low_price: float = 0.0
        self.last_price: float = 0.0
        self.date: datetime.date = None

    def on_message(self, d: dict) -> None:
        """Websocket订单簿更新推送"""
        # print("@@@OrderBook",d)
        type: str = d["type"]
        channel: str = d["channel"]
        dt: datetime = datetime.now(UTC_TZ)
        if type == "subscribed" and channel == "v3_orderbook":
            self.on_snapshot(d["contents"]["asks"], d["contents"]["bids"], dt)
        elif type == "channel_batch_data" and channel == "v3_orderbook":
            self.on_update(d["contents"], dt)
        elif channel == "v3_trades":
            self.on_trades(d["contents"]["trades"], dt)

    def on_trades(self, d: list, dt) -> None:
        """成交更新推送"""
        price_list: list = []
        for n in range(len(d)):
            price: float = float(d[n]["price"])
            price_list.append(price)

        tick: TickData = self.tick
        tick.datetime = generate_datetime(d[0]["createdAt"])

        if not self.date:
            self.date = tick.datetime.date()

        if tick.datetime.date() != self.date:
            req: HistoryRequest = HistoryRequest(
                symbol=tick.symbol,
                exchange=Exchange.DYDX,
                start=None,
                end=None,
                interval=Interval.DAILY
            )
            history: list[BarData] = self.gateway.query_history(req)
            self.open_price = history[0].open_price
        tick.localtime = datetime.now()
        tick.trade_price = float(d[0]["price"])
        tick.trade_volume = float(d[0]["size"])
        self.gateway.on_tick(copy(tick))

    def on_update(self, ddd: dict, dt) -> None:
        """盘口更新推送"""
        for d in ddd:
            offset: int = int(d["offset"])
            if offset < self.offset:
                return
            self.offset = offset
            # 
            for price, ask_volume in d["asks"]:
                price: float = float(price)
                ask_volume: float = float(ask_volume)
                if price in self.asks:
                    if ask_volume > 0 :
                        ask_volume: float = float(ask_volume)
                        self.asks[price] = ask_volume
                    else:
                        self.asks.pop(price)
                else:
                    if ask_volume > 0:
                        self.asks[price] = ask_volume

            for price, bid_volume in d["bids"]:
                price: float = float(price)
                bid_volume: float = float(bid_volume)
                if price in self.bids:
                    if bid_volume > 0 :
                        self.bids[price] = bid_volume
                    else:
                        self.bids.pop(price)
                else:
                    if bid_volume > 0:
                        self.bids[price] = bid_volume
            
            if len(d["asks"]) > 0:
                self.depth.volume = float(d["asks"][0][0])
                self.depth.price = float(d["asks"][0][1])
                self.depth.direction = Direction.SHORT
            if len(d["bids"]) > 0:
                self.depth.volume = float(d["bids"][0][0])
                self.depth.price = float(d["bids"][0][1])
                self.depth.direction = Direction.LONG

        depth = self.depth
        depth.localtime = datetime.now()
        depth.datetime = dt
        self.gateway.on_depth(copy(depth))
        self.generate_tick(dt)


    def on_snapshot(self, asks, bids, dt: datetime) -> None:
        """盘口推送回报"""
        for n in range(len(asks)):
            price = asks[n]["price"]
            volume = asks[n]["size"]

            self.asks[float(price)] = float(volume)

        for n in range(len(bids)):
            price = bids[n]["price"]
            volume = bids[n]["size"]

            self.bids[float(price)] = float(volume)

        self.generate_tick(dt)

    def generate_tick(self, dt: datetime) -> None:
        """合成tick"""
        tick: TickData = self.tick

        for k in list(self.bids.keys()):
            if k > self.tick.trade_price:
                self.bids.pop(k)
        bids_keys: list = self.bids.keys()
        bids_keys: list = sorted(bids_keys, reverse=True)

        # print("self.bids",self.bids)
        for i in range(min(5, len(bids_keys))):
            price: float = float(bids_keys[i])
            volume: float = float(self.bids[bids_keys[i]])
            setattr(tick, f"bid_price_{i + 1}", price)
            setattr(tick, f"bid_volume_{i + 1}", volume)

        for k in list(self.asks.keys()):
            if k < self.tick.trade_price:
                self.asks.pop(k)
        asks_keys: list = self.asks.keys()
        asks_keys: list = sorted(asks_keys)

        for i in range(min(5, len(asks_keys))):
            price: float = float(asks_keys[i])
            volume: float = float(self.asks[asks_keys[i]])
            setattr(tick, f"ask_price_{i + 1}", price)
            setattr(tick, f"ask_volume_{i + 1}", volume)
        
        tick.best_ask_price = tick.ask_price_1
        tick.best_ask_volume = tick.ask_volume_1
        tick.best_bid_price = tick.bid_price_1
        tick.best_bid_volume = tick.bid_volume_1
        tick.datetime = dt
        tick.localtime = datetime.now()
        # 盘口更新时，不推送tick
        # self.gateway.on_tick(copy(tick))
