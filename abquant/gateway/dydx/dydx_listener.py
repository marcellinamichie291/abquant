from logging import WARNING
from abquant.gateway import accessor
from abquant.gateway.dydx.dydx_accessor import generate_now_iso
from abquant.trader.utility import round_to
from datetime import datetime
from typing import Dict, List, Optional
from copy import copy, deepcopy

from . import DIRECTION_DYDX2AB, DIRECTION_AB2DYDX, WEBSOCKET_HOST, TESTNET_WEBSOCKET_HOST, REST_HOST, TESTNET_REST_HOST, ORDERTYPE_AB2DYDX, STATUS_DYDX2AB,ORDERTYPE_DYDX2AB, symbol_contract_map
from ..basegateway import Gateway
from ..listener import WebsocketListener
from abquant.trader.exception import MarketException
from abquant.trader.common import Direction, Exchange
from abquant.trader.object import AccountData, PositionData, SubscribeRequest
from abquant.trader.msg import DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
import pytz
from dydx_util import *

UTC_TZ = pytz.utc

class DydxWebsocketListener(WebsocketListener):
    """
    dydx websocket，
    委托、资金、持仓
    
    """
    def __init__(self, gateway: Gateway):
        super().__init__()

        self.gateway = gateway
        self.gateway_name

        self.subscribed: Dict[str, SubscribeRequest] = {}
        self.orderbooks: Dict[str, "OrderBook"] = {}


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
            name=symbol_contract_map[symbol].name,
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
        type: str = d["type"]
        channel: str = d["channel"]
        dt: datetime = datetime.now(UTC_TZ)
        if type == "subscribed" and channel == "v3_orderbook":
            self.on_snapshot(d["contents"]["asks"], d["contents"]["bids"], dt)
        elif type == "channel_data" and channel == "v3_orderbook":
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
        tick.high_price = max(self.high_price, max(price_list))
        tick.low_price = min(self.low_price, min(price_list))
        tick.last_price = float(d[0]["price"])
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

        tick.open_price = self.open_price
        tick.localtime = datetime.now()

        self.gateway.on_tick(copy(tick))

    def on_update(self, d: dict, dt) -> None:
        """盘口更新推送"""
        offset: int = int(d["offset"])
        if offset < self.offset:
            return
        self.offset = offset

        for price, ask_volume in d["asks"]:
            price: float = float(price)
            ask_volume: float = float(ask_volume)
            if price in self.asks:
                if ask_volume > 0:
                    ask_volume: float = float(ask_volume)
                    self.asks[price] = ask_volume
                else:
                    del self.asks[price]
            else:
                if ask_volume > 0:
                    self.asks[price] = ask_volume

        for price, bid_volume in d["bids"]:
            price: float = float(price)
            bid_volume: float = float(bid_volume)
            if price in self.bids:
                if bid_volume > 0:
                    self.bids[price] = bid_volume
                else:
                    del self.bids[price]
            else:
                if bid_volume > 0:
                    self.bids[price] = bid_volume

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

        bids_keys: list = self.bids.keys()
        bids_keys: list = sorted(bids_keys, reverse=True)

        for i in range(min(5, len(bids_keys))):
            price: float = float(bids_keys[i])
            volume: float = float(self.bids[bids_keys[i]])
            setattr(tick, f"bid_price_{i + 1}", price)
            setattr(tick, f"bid_volume_{i + 1}", volume)

        asks_keys: list = self.asks.keys()
        asks_keys: list = sorted(asks_keys)

        for i in range(min(5, len(asks_keys))):
            price: float = float(asks_keys[i])
            volume: float = float(self.asks[asks_keys[i]])
            setattr(tick, f"ask_price_{i + 1}", price)
            setattr(tick, f"ask_volume_{i + 1}", volume)

        tick.datetime = dt
        tick.localtime = datetime.now()
        self.gateway.on_tick(copy(tick))