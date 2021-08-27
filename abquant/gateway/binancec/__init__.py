
from datetime import timedelta
from enum import Enum
from typing import Dict, Tuple
from abquant.trader.common import Direction, Interval, OrderType, Status
from abquant.trader.object import ContractData

F_REST_HOST: str = "https://fapi.binance.com"
F_WEBSOCKET_TRADE_HOST: str = "wss://fstream.binance.com/ws/"
F_WEBSOCKET_DATA_HOST: str = "wss://fstream.binance.com/stream?streams="

F_TESTNET_RESTT_HOST: str = "https://testnet.binancefuture.com"
F_TESTNET_WEBSOCKET_TRADE_HOST: str = "wss://stream.binancefuture.com/ws/"
F_TESTNET_WEBSOCKET_DATA_HOST: str = "wss://stream.binancefuture.com/stream?streams="

D_REST_HOST: str = "https://dapi.binance.com"
D_WEBSOCKET_TRADE_HOST: str = "wss://dstream.binance.com/ws/"
D_WEBSOCKET_DATA_HOST: str = "wss://dstream.binance.com/stream?streams="

D_TESTNET_RESTT_HOST: str = "https://testnet.binancefuture.com"
D_TESTNET_WEBSOCKET_TRADE_HOST: str = "wss://dstream.binancefuture.com/ws/"
D_TESTNET_WEBSOCKET_DATA_HOST: str = "wss://dstream.binancefuture.com/stream?streams="

STATUS_BINANCEC2AB: Dict[str, Status] = {
    "NEW": Status.NOTTRADED,
    "PARTIALLY_FILLED": Status.PARTTRADED,
    "FILLED": Status.ALLTRADED,
    "CANCELED": Status.CANCELLED,
    "REJECTED": Status.REJECTED,
    "EXPIRED": Status.CANCELLED
}

ORDERTYPE_AB2BINANCEC: Dict[OrderType, Tuple[str, str]] = {
    OrderType.LIMIT: ("LIMIT", "GTC"),
    OrderType.MARKET: ("MARKET", "GTC"),
    # TODO
    # fak: ("LIMIT", "IOC"),
    # fok: ("LIMIT", "FOK"),
}
ORDERTYPE_BINANCEC2AB: Dict[Tuple[str, str], OrderType] = {v: k for k, v in ORDERTYPE_AB2BINANCEC.items()}

DIRECTION_AB2BINANCEC: Dict[Direction, str] = {
    Direction.LONG: "BUY",
    Direction.SHORT: "SELL"
}
DIRECTION_BINANCEC2AB: Dict[str, Direction] = {v: k for k, v in DIRECTION_AB2BINANCEC.items()}

INTERVAL_AB2BINANCEC: Dict[Interval, str] = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "1h",
    Interval.DAILY: "1d",
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
