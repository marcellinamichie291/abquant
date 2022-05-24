from datetime import datetime
from typing import Any, Callable, Dict
from copy import copy

from abquant.trader.common import Direction, Exchange, Offset
from abquant.trader.msg import DepthData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import AccountData, PositionData, SubscribeRequest
from ..basegateway import Gateway
from ..listener import WebsocketListener

from . import (
    DIRECTION_BYBIT2AB,
    SPOT_WEBSOCKET_HOST,
    ORDER_TYPE_BYBIT2AB,
    STATUS_BYBIT2AB,
    TESTNET_SPOT_WEBSOCKET_HOST,
    local_orderids,
    )

from .bybit_util import generate_datetime, generate_datetime_2, generate_timestamp, get_float_value, sign


class BybitSpotMarketWebsocketListener(WebsocketListener):
    """现货行情Websocket接口"""

    def __init__(self, gateway: Gateway) -> None:
        """构造函数"""
        super(BybitSpotMarketWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 30

        self.ticks: Dict[str, TickData] = {}
        self.transactions: Dict[str, TransactionData] = {}
        self.depths: Dict[str, DepthData] = {}

        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.symbol_bids: Dict[str, dict] = {}
        self.symbol_asks: Dict[str, dict] = {}

    def connect(self, server: str, proxy_host: str, proxy_port: int):
        """ws行情"""

        if server == "REAL":
            url = SPOT_WEBSOCKET_HOST
        else:
            url = TESTNET_SPOT_WEBSOCKET_HOST
        self.init(url, proxy_host, proxy_port)

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
        
        # 缓存订阅记录
        self.subscribed[req.symbol] = req

        symbol = req.symbol

        tick, depth, transaction, _ = self.make_data(symbol, Exchange.BYBIT, datetime.now(), self.gateway_name)
        self.ticks[symbol] = tick
        self.transactions[symbol] = transaction
        self.depths[symbol] = depth

        # 发送订阅请求
        subscribe_mode = self.gateway.subscribe_mode
        params = {
            "symbol": symbol,
            "binary": False
        }
        if subscribe_mode.best_tick or subscribe_mode.tick_5:
            req_dict: dict = {
                "topic": "bookTicker",
                "event": "sub",
                "params": params
            }
            self.send_packet(req_dict)
        if subscribe_mode.depth:
            req_dict: dict = {
                "topic": "depth",
                "event": "sub",
                "params": params
            }
            self.send_packet(req_dict)
        if subscribe_mode.transaction:
            req_dict: dict = {
                "topic": "trade",
                "event": "sub",
                "params": params
            }
            self.send_packet(req_dict)

    def on_packet(self, packet: dict):
        if "topic" not in packet:
            return
        channel: str = packet["topic"]

        if "bookTicker" in channel:
            # best_tick
            type_: str = packet["type"]
            data: dict = packet["data"]
            symbol: str = channel.replace("instrument_info.100ms.", "")
            tick: TickData = self.ticks[symbol]
            if type_ == "snapshot":
                if not data["last_price"]:  # 过滤最新价为0的数据
                    return

                tick.trade_price = float(data["last_price"])
                tick.trade_volume = int(data["volume_24h_e8"]) / 100000000
                tick.datetime = generate_datetime(data["updated_at"])

            else:
                update: dict = data["update"][0]

                if "last_price" not in update:  # 过滤最新价为0的数据
                    return

                tick.trade_price = float(update["last_price"])
                if update["volume_24h_e8"]:
                    tick.trade_volume = int(update["volume_24h_e8"]) / 100000000
                tick.datetime = generate_datetime(update["updated_at"])

            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))

        if "trade" in channel:
            # transaction
            symbol: str = channel.replace("trade.", "")
            l = packet["data"]
            for data in l:
                transaction: TradeData = self.transactions[symbol]
                tick: TickData = self.ticks[symbol]
                dt = generate_datetime_2(int(data["trade_time_ms"]) / 1000)
                dt_now = datetime.now()
                p = float(data["price"])
                v = data["size"]
                
                tick.trade_price = p
                tick.trade_volume = v
                tick.datetime = dt
                tick.localtime = dt_now
                
                transaction.datetime = dt
                transaction.volume = v
                transaction.price = p
                transaction.direction = Direction.SHORT if data["side"] == "Sell" else Direction.LONG
                
                self.gateway.on_tick(copy(tick))
                self.gateway.on_transaction(copy(transaction))

        if "depth" in channel:
            # depth
            symbol: str = channel.replace("orderBook_200.100ms.", "")
            type_: str = packet["type"]
            data: dict = packet["data"]
            depth: DepthData = self.depths[symbol]
            depth.localtime = datetime.now()
            if not data:
                return

            depth.datetime = generate_datetime_2(int(packet["timestamp_e6"]) / 1000000)
            if type_ == "snapshot":
                buf = data["order_book"]
                for d in buf:
                    depth.price = float(d["price"])
                    depth.volume = d["size"]
                    depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                    self.gateway.on_depth(copy(depth))
            else:
                for key, buf in data.items():
                    if key == "delete":
                        for d in buf:
                            depth.price = float(d["price"])
                            depth.volume = 0
                            depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                            self.gateway.on_depth(copy(depth))

                    if key == "update" or key == "insert":
                        for d in buf:
                            depth.price = float(d["price"])
                            depth.volume = d["size"]
                            depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                            self.gateway.on_depth(copy(depth))

