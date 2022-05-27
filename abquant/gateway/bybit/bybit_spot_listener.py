from datetime import datetime
from typing import Any, Callable, Dict
from copy import copy
from logging import WARNING

from abquant.trader.common import Direction, Exchange, Offset
from abquant.trader.msg import DepthData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import AccountData, PositionData, SubscribeRequest
from abquant.trader.exception import MarketException
from ..basegateway import Gateway
from ..listener import WebsocketListener

from . import (
    DIRECTION_BYBIT2AB,
    SPOT_WEBSOCKET_HOST,
    ORDER_TYPE_BYBIT2AB,
    STATUS_BYBIT2AB,
    TESTNET_SPOT_WEBSOCKET_HOST,
    symbol_contract_map,
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
        if req.symbol not in symbol_contract_map:
            self.gateway.write_log(f"找不到该合约代码{req.symbol}", level=WARNING)
            return

        symbol = req.symbol.lower()     # 本地小写索引

        # 缓存订阅记录
        self.subscribed[symbol] = req

        tick, depth, transaction, _ = self.make_data(symbol, Exchange.BYBIT, datetime.now(), self.gateway_name)
        self.ticks[symbol] = tick
        self.transactions[symbol] = transaction
        self.depths[symbol] = depth

        # 发送订阅请求
        symbol = symbol.upper()         # 交易所大写参数
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
        params: dict = packet["params"]
        data: dict = packet.get("data",None)
        symbol: str = params["symbol"].lower()
        if not data:
            return

        if "bookTicker" == channel:
            # best_tick
            tick: TickData = self.ticks[symbol]

            tick.trade_price = 0
            tick.trade_volume = 0
            tick.best_bid_price = float(data["bidPrice"])
            tick.best_bid_volume = float(data["bidQty"])
            tick.best_ask_price = float(data["askPrice"])
            tick.best_ask_volume = float(data["askQty"])
            tick.datetime = generate_datetime_2(int(data["time"]) / 1000)
            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))

        elif "trade" == channel:
            # transaction
            transaction: TradeData = self.transactions[symbol]
            tick: TickData = self.ticks[symbol]

            dt = generate_datetime_2(int(data["t"]) / 1000)
            dt_now = datetime.now()
            p = float(data["p"])
            v = float(data["q"])

            tick.trade_price = p
            tick.trade_volume = v
            tick.datetime = dt
            tick.localtime = dt_now

            transaction.tradeid = data["v"]
            transaction.datetime = dt
            transaction.volume = v
            transaction.price = p
            transaction.direction = Direction.LONG if bool(data["m"]) == True else Direction.SHORT

            self.gateway.on_tick(copy(tick))
            self.gateway.on_transaction(copy(transaction))

        elif "depth" == channel:
            # depth
            depth: DepthData = self.depths[symbol]

            depth.localtime = datetime.now()
            depth.datetime = generate_datetime_2(int(data["t"]) / 1000)
            depth.symbol = symbol

            for p, v in data['a']:
                depth.volume = float(v)
                depth.price = float(p)
                depth.direction = Direction.SHORT
                self.gateway.on_depth(copy(depth))

            for p, v in data['b']:
                depth.volume = float(v)
                depth.price = float(p)
                depth.direction = Direction.LONG
                self.gateway.on_depth(copy(depth))

            # tick_5
            tick: TickData = self.ticks[symbol]
            newest = generate_datetime_2(int(data['t']) / 1000)

            # clear transaction inforamtion
            tick.trade_price = 0
            tick.trade_volume = 0

            bids = data["b"]
            for n in range(min(5, len(bids))):
                price, volume = bids[n]
                tick.__setattr__("bid_price_" + str(n + 1), float(price))
                tick.__setattr__("bid_volume_" + str(n + 1), float(volume))

            asks = data["a"]
            for n in range(min(5, len(asks))):
                price, volume = asks[n]
                tick.__setattr__("ask_price_" + str(n + 1), float(price))
                tick.__setattr__("ask_volume_" + str(n + 1), float(volume))

            # tick time checkout to update best ask/bid
            if newest is not None and tick.datetime < newest and self.gateway.subscribe_mode.best_tick:
                tick.datetime = newest
                tick.best_ask_price = tick.ask_price_1
                tick.best_ask_volume = tick.ask_volume_1
                tick.best_bid_price = tick.bid_price_1
                tick.best_bid_volume = tick.bid_volume_1
            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))
        
        else: 
            raise MarketException("Unrecognized channel from {}: packet content, \n{}".format(self.gateway_name, packet))