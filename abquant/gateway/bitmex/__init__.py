import hashlib
import hmac
import sys
import time
from copy import copy
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict
from urllib.parse import urlencode
from requests import ConnectionError

from abquant.trader.object import ContractData
from abquant.trader.common import Direction, Interval, OrderType, Status

REST_HOST = "https://www.bitmex.com/api/v1"
WEBSOCKET_HOST = "wss://ws.bitmex.com/realtime"

TESTNET_REST_HOST = "https://testnet.bitmex.com/api/v1"
TESTNET_WEBSOCKET_HOST = "wss://ws.testnet.bitmex.com/realtime"

STATUS_BITMEX2AB = {
    "New": Status.NOTTRADED,
    "Partially filled": Status.PARTTRADED,
    "Filled": Status.ALLTRADED,
    "Canceled": Status.CANCELLED,
    "Rejected": Status.REJECTED,
}

DIRECTION_AB2BITMEX = {Direction.LONG: "Buy", Direction.SHORT: "Sell"}
DIRECTION_BITMEX2AB = {v: k for k, v in DIRECTION_AB2BITMEX.items()}

ORDERTYPE_AB2BITMEX = {
    OrderType.LIMIT: "Limit",
    OrderType.MARKET: "Market",
    # stop order?: "Stop"
}
ORDERTYPE_BITMEX2AB = {v: k for k, v in ORDERTYPE_AB2BITMEX.items()}
ORDERTYPE_AB2BITMEX[OrderType.POSTONLYLIMIT] = "Limit"

INTERVAL_AB2BITMEX = {
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
