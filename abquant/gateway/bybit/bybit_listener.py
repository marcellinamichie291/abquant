from datetime import datetime
from typing import Any, Callable, Dict
from copy import copy

from abquant.trader.common import Exchange, Offset
from abquant.trader.msg import OrderData, TickData, TradeData
from abquant.trader.object import AccountData, PositionData, SubscribeRequest
from ..basegateway import Gateway
from ..listener import WebsocketListener

from . import (
    DIRECTION_BYBIT2AB, 
    ORDER_TYPE_BYBIT2AB, 
    PRIVATE_WEBSOCKET_HOST, 
    PUBLIC_WEBSOCKET_HOST, 
    STATUS_BYBIT2AB, 
    TESTNET_PRIVATE_WEBSOCKET_HOST, 
    TESTNET_PUBLIC_WEBSOCKET_HOST, 
    local_orderids,
    symbol_contract_map)

from .bybit_util import generate_datetime, generate_datetime_2, generate_timestamp, sign

class BybitMarketWebsocketListener(WebsocketListener):
    """U本位合约的行情Websocket接口"""

    def __init__(self, gateway: Gateway) -> None:
        """构造函数"""
        super(BybitMarketWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 30

        self.ticks: Dict[str, TickData] = {}
        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.symbol_bids: Dict[str, dict] = {}
        self.symbol_asks: Dict[str, dict] = {}

    def connect(self, server: str, proxy_host: str, proxy_port: int):
        """ws行情"""

        if server == "REAL":
            url = PUBLIC_WEBSOCKET_HOST
        else:
            url = TESTNET_PUBLIC_WEBSOCKET_HOST
        self.init(url, proxy_host, proxy_port)
        self.start()

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接成功")

        for req in list(self.subscribed.values()):
            self.subscribe(req)

    def on_disconnected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接断开")

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        
        if req.symbol not in symbol_contract_map:
            self.gateway.write_log(f"找不到该合约代码{req.symbol}")
            return
        # 缓存订阅记录
        self.subscribed[req.symbol] = req

        # # 创建TICK对象
        tick: TickData = TickData(
            symbol=req.symbol,
            exchange=req.exchange,
            datetime=datetime.now(),
            gateway_name=self.gateway_name
        )
        self.ticks[req.symbol] = tick

        # 发送订阅请求
        
        req_dict: dict = {
            "op": "subscribe", 
            "args": [
                f"instrument_info.100ms.{req.symbol}",
                f"orderBookL2_25.{req.symbol}",
                # f"trade.{req.symbol}",
            ]
        }
        self.send_packet(req_dict)
    

    def on_packet(self, packet: dict):
        if "topic" not in packet:
            return
        channel = packet["topic"]

        if "orderBookL2_25" in  channel:
            self.on_depth(packet)
        if "instrument_info" in channel:
            self.on_tick(packet)

    def on_tick(self, packet: dict) -> None:
        """行情推送回报"""
        topic: str = packet["topic"]
        type_: str = packet["type"]
        data: dict = packet["data"]

        symbol: str = topic.replace("instrument_info.100ms.", "")
        tick: TickData = self.ticks[symbol]

        if type_ == "snapshot":
            if not data["last_price"]:           # 过滤最新价为0的数据
                return

            tick.trade_price = float(data["last_price"])

            tick.trade_volume = int(data["volume_24h_e8"]) / 100000000

            tick.datetime = generate_datetime(data["updated_at"])

        else:
            update: dict = data["update"][0]

            if "last_price" not in update:      # 过滤最新价为0的数据
                return

            tick.trade_price = float(update["last_price"])

            if update["volume_24h_e8"]:

                tick.trade_volume = int(update["volume_24h_e8"]) / 100000000

            tick.datetime = generate_datetime(update["updated_at"])
            
        tick.localtime = datetime.now()
        self.gateway.on_tick(copy(tick))

    def on_depth(self, packet: dict) -> None:
        """盘口推送回报"""
        topic: str = packet["topic"]
        type_: str = packet["type"]
        data: dict = packet["data"]
        if not data:
            return

        symbol: str = topic.replace("orderBookL2_25.", "")
        tick: TickData = self.ticks[symbol]
        bids: dict = self.symbol_bids.setdefault(symbol, {})
        asks: dict = self.symbol_asks.setdefault(symbol, {})

        if type_ == "snapshot":

            buf: list = data["order_book"]

            for d in buf:
                price: float = float(d["price"])

                if d["side"] == "Buy":
                    bids[price] = d
                else:
                    asks[price] = d
        else:
            for d in data["delete"]:
                price: float = float(d["price"])

                if d["side"] == "Buy":
                    bids.pop(price)
                else:
                    asks.pop(price)

            for d in (data["update"] + data["insert"]):

                price: float = float(d["price"])
                if d["side"] == "Buy":
                    bids[price] = d
                else:
                    asks[price] = d

        bid_keys: list = list(bids.keys())
        bid_keys.sort(reverse=True)

        ask_keys: list = list(asks.keys())
        ask_keys.sort()

        for i in range(5):
            n = i + 1

            bid_price = bid_keys[i]
            bid_data = bids[bid_price]
            ask_price = ask_keys[i]
            ask_data = asks[ask_price]

            setattr(tick, f"bid_price_{n}", bid_price)
            setattr(tick, f"bid_volume_{n}", bid_data["size"])
            setattr(tick, f"ask_price_{n}", ask_price)
            setattr(tick, f"ask_volume_{n}", ask_data["size"])

        tick.datetime = generate_datetime_2(int(packet["timestamp_e6"]) / 1000000)
        tick.localtime = datetime.now()
        self.gateway.on_tick(copy(tick))


class BybitTradeWebsocketListener(WebsocketListener):
    """u本位 合约的交易Websocket接口"""

    def __init__(self, gateway: Gateway) -> None:
        """构造函数"""
        super(BybitTradeWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 30

        self.key: str = ""
        self.secret: bytes = b""
        self.server: str = ""

        self.callbacks: Dict[str, Callable] = {}
        self.ticks: Dict[str, TickData] = {}
        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.symbol_bids: Dict[str, dict] = {}
        self.symbol_asks: Dict[str, dict] = {}

    def connect(
        self,
        key: str,
        secret: str,
        server: str,
        proxy_host: str,
        proxy_port: int
    ) -> None:
        """连接Websocket私有频道"""
        self.key = key
        self.secret = secret.encode()
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.server = server

        if self.server == "REAL":
            url = PRIVATE_WEBSOCKET_HOST
        else:
            url = TESTNET_PRIVATE_WEBSOCKET_HOST

        self.init(url, self.proxy_host, self.proxy_port)
        self.start()

    def login(self) -> None:
        """用户登录"""
        expires: int = generate_timestamp(30)
        msg = f"GET/realtime{int(expires)}"
        signature: str = sign(self.secret, msg.encode())

        req: dict = {
            "op": "auth",
            "args": [self.key, expires, signature]
        }
        self.send_packet(req)

    def subscribe_topic(
        self,
        topic: str,
        callback: Callable[[str, dict], Any]
    ) -> None:
        """订阅私有频道"""
        self.callbacks[topic] = callback

        req: dict = {
            "op": "subscribe",
            "args": [topic],
        }
        self.send_packet(req)

    def on_connected(self) -> None:
        """连接成功回报"""
        self.gateway.write_log("交易Websocket API连接成功")
        self.login()

    def on_disconnected(self) -> None:
        """连接断开回报"""
        self.gateway.write_log("交易Websocket API连接断开")

    def on_packet(self, packet: dict) -> None:
        """推送数据回报"""
        if "topic" not in packet:
            op: str = packet["request"]["op"]
            if op == "auth":
                self.on_login(packet)
        else:
            channel: str = packet["topic"]
            callback: callable = self.callbacks[channel]
            callback(packet)

    def on_login(self, packet: dict):
        """用户登录请求回报"""
        success: bool = packet.get("success", False)
        if success:

            self.subscribe_topic("order", self.on_order)
            self.subscribe_topic("execution", self.on_trade)
            self.subscribe_topic("position", self.on_position)
            self.subscribe_topic("wallet", self.on_account)

        else:
            self.gateway.write_log("交易Websocket API登录失败")

    def on_account(self, packet: dict) -> None:
        """资金更新推送"""
        for d in packet["data"]:
            account = AccountData(
                accountid="USDT",
                balance=d["wallet_balance"],
                frozen=d["wallet_balance"] - d["available_balance"],
                gateway_name=self.gateway_name,
            )
            self.gateway.on_account(account)

    def on_trade(self, packet: dict) -> None:
        """成交更新推送"""
        for d in packet["data"]:
            orderid: str = d["order_link_id"]
            if not orderid:
                orderid: str = d["order_id"]

            trade: TradeData = TradeData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                orderid=orderid,
                tradeid=d["exec_id"],
                direction=DIRECTION_BYBIT2AB[d["side"]],
                price=float(d["price"]),
                volume=d["exec_qty"],
                datetime=generate_datetime(d["trade_time"]),
                gateway_name=self.gateway_name,
            )

            self.gateway.on_trade(trade)

    def on_order(self, packet: dict) -> None:
        """委托更新推送"""
        for d in packet["data"]:
            orderid: str = d["order_link_id"]
            if orderid:
                local_orderids.add(orderid)
            else:
                orderid: str = d["order_id"]

            dt: datetime = generate_datetime(d["create_time"])

            order: OrderData = OrderData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                orderid=orderid,
                type=ORDER_TYPE_BYBIT2AB[d["order_type"]],
                direction=DIRECTION_BYBIT2AB[d["side"]],
                price=float(d["price"]),
                volume=d["qty"],
                traded=d["cum_exec_qty"],
                status=STATUS_BYBIT2AB[d["order_status"]],
                datetime=dt,
                gateway_name=self.gateway_name
            )
            offset: bool = d["reduce_only"]
            if offset:
                order.offset = Offset.CLOSE
            else:
                order.offset = Offset.OPEN

            self.gateway.on_order(order)

    def on_position(self, packet: dict) -> None:
        """持仓更新推送"""
        for d in packet["data"]:
            position: PositionData = PositionData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                direction=DIRECTION_BYBIT2AB[d["side"]],
                volume=d["size"],
                price=float(d["entry_price"]),
                gateway_name=self.gateway_name
            )
            self.gateway.on_position(position)

