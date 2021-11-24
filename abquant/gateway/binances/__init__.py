from datetime import timedelta

from enum import Enum
from typing import Dict
from abquant.trader.msg import Status, OrderType, Direction, Interval
from abquant.trader.object import ContractData


REST_HOST = "https://www.binance.com"
WEBSOCKET_TRADE_HOST = "wss://stream.binance.com:9443/ws/"
WEBSOCKET_DATA_HOST = "wss://stream.binance.com:9443/stream?streams="

STATUS_BINANCE2AB = {
    "NEW": Status.NOTTRADED,
    "PARTIALLY_FILLED": Status.PARTTRADED,
    "FILLED": Status.ALLTRADED,
    "CANCELED": Status.CANCELLED,
    "REJECTED": Status.REJECTED
}


ORDERTYPE_AB2BINANCE = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET"
}
ORDERTYPE_BINANCE2AB = {v: k for k, v in ORDERTYPE_AB2BINANCE.items()}

DIRECTION_AB2BINANCE = {
    Direction.LONG: "BUY",
    Direction.SHORT: "SELL"
}
DIRECTION_BINANCE2AB = {v: k for k, v in DIRECTION_AB2BINANCE.items()}

INTERVAL_AB2BINANCE = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "1h",
    Interval.DAILY: "1d",
}

TIMEDELTA_MAP = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta(days=1),
}


symbol_contract_map: Dict[str, ContractData] = {}

class Security(Enum):
    NONE = 0
    SIGNED = 1
    API_KEY = 2

