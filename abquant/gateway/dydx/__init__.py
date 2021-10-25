# -*- encoding: utf-8 -*-
'''
@File    :   __init__.py
@Time    :   2021/10/19 14:23:49
@Version :   1.0
@Desc    :   参考vnpy_dydx
'''

from datetime import timedelta
from enum import Enum
from typing import Dict, Tuple

from abquant.trader.common import Direction, Interval, OrderType, Status
from abquant.trader.object import ContractData


# 实盘REST API地址
REST_HOST: str = "https://api.dydx.exchange"

# 实盘Websocket API地址
WEBSOCKET_HOST: str = "wss://api.dydx.exchange/v3/ws"

# 模拟盘REST API地址
TESTNET_REST_HOST: str = "https://api.stage.dydx.exchange"

# 模拟盘Websocket API地址
TESTNET_WEBSOCKET_HOST: str = "wss://api.stage.dydx.exchange/v3/ws"

STATUS_DYDX2AB: Dict[str, Status] = {
    "PENDING": Status.NOTTRADED,
    "OPEN": Status.NOTTRADED,
    "FILLED": Status.ALLTRADED,
    "CANCELED": Status.CANCELLED
}

ORDERTYPE_AB2DYDX: Dict[OrderType, Tuple[str, str]] = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET"
    # OrderType.LIMIT: ("LIMIT", "GTC"),
    # OrderType.MARKET: ("MARKET", "GTC"),
    # TODO
    # fak: ("LIMIT", "IOC"),
    # fok: ("LIMIT", "FOK"),
}
ORDERTYPE_DYDX2AB: Dict[Tuple[str, str], OrderType] = {v: k for k, v in ORDERTYPE_AB2DYDX.items()}

DIRECTION_AB2DYDX: Dict[Direction, str] = {
    Direction.LONG: "BUY",
    Direction.SHORT: "SELL"
}
DIRECTION_DYDX2AB: Dict[str, Direction] = {v: k for k, v in DIRECTION_AB2DYDX.items()}

INTERVAL_AB2DYDX: Dict[Interval, str] = {
    Interval.MINUTE: "1MIN",
    Interval.HOUR: "1HOUR",
    Interval.DAILY: "1DAY",
}

TIMEDELTA_MAP: Dict[Interval, timedelta] = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta(days=1),
}

class Security(Enum):
    NONE: int = 0
    SIGNED: int = 1
    API_KEY: int = 2

symbol_name_map: Dict[str, str] = {}
symbol_contract_map: Dict[str, ContractData] = {}
