#! /usr/bin/env/Python
# -*- coding:utf-8 -*-
"""
@author: baijy
@time: 2022/5/11 9:27 AM
@desc:
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Set

from abquant.trader.common import Direction, Interval, OrderType, Product
from abquant.trader.object import ContractData

# REST API地址
REST_HOST: str = 'https://api.gateio.ws'
REST_PREFIX: str = '/api/v4'
END_POINT: str = REST_HOST + REST_PREFIX

# Websocket API地址
WEBSOCKET_HOST: str = 'wss://api.gateio.ws/ws/v4/'

# 委托类型映射
ORDERTYPE_AB2GATE = {
    OrderType.LIMIT: "limit",
    OrderType.MARKET: "market"
}

ORDERTYPE_GATE2AB = {v: k for k, v in ORDERTYPE_AB2GATE.items()}

# 买卖方向映射
DIRECTION_AB2GATE = {
    Direction.LONG: "buy",
    Direction.SHORT: "sell",
    Direction.NET: "net"
}

DIRECTION_GATE2AB = {v: k for k, v in DIRECTION_AB2GATE.items()}

# 商品类型映射
PRODUCTTYPE_AB2GATE = {
    Product.FUTURES: "future",
    Product.SPOT: "spot"
}

PRODUCTTYPE_GATE2AB = {v: k for k, v in PRODUCTTYPE_AB2GATE.items()}

# 窗口长度映射
INTERVAL_AB2FTX = {
    Interval.MINUTE: 60,
    Interval.HOUR: 3600,
    Interval.DAILY: 86400,
    Interval.WEEKLY: 604800
}

INTERVAL_FTX2AB = {v: k for k, v in INTERVAL_AB2FTX.items()}

# 历史数据长度限制映射
LIMIT_AB2FTX = {
    Interval.MINUTE: 950,
    Interval.HOUR: 1400,
    Interval.DAILY: 1400,
    Interval.WEEKLY: 1400
}

# 合约数据全局缓存字典
symbol_contract_map: Dict[str, ContractData] = {}

# 本地委托号缓存集合
local_orderids: Set[str] = set()


# 鉴权类型
class Security(Enum):
    NONE: int = 0
    SIGNED: int = 1


def change_datetime(created_time: str) -> datetime:
    """转换时间"""
    dt = datetime.strptime(created_time[:-6], "%Y-%m-%dT%H:%M:%S.%f")
    return dt


def generate_datetime(timestamp: float) -> datetime:
    """生成时间"""
    dt: datetime = datetime.fromtimestamp(timestamp)
    return dt