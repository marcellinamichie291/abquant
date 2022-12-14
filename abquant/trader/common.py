
from enum import Enum


class Direction(Enum):
    """
    Direction of order/trade/position.
    """
    LONG = "多"
    SHORT = "空"
    NET = "净"


class Offset(Enum):
    """
    Offset of order/trade.
    """
    NONE = ""
    OPEN = "开"
    CLOSE = "平"


class Status(Enum):
    """
    Order status.
    """
    SUBMITTING = "提交中"
    NOTTRADED = "未成交"
    PARTTRADED = "部分成交"
    ALLTRADED = "全部成交"
    CANCELLED = "已撤销"
    REJECTED = "拒单"
    # TODO 
    TIMEOUT = "超时未回报"

class Product(Enum):
    """
    Product class.
    """
    FUTURES = "期货"
    OPTION = "期权"
    SPOT = "现货"


class OrderType(Enum):
    """
    Order type.
    """
    LIMIT = "限价"
    MARKET = "市价"
    POSTONLYLIMIT = "POSTONLY限价单"
    STOP = "STOP"
    FAK = "FAK"
    FOK = "FOK"
    STOP_LIMIT = "止损"
    TRAILING_STOP = "追踪止损"
    TAKE_PROFIT = "止盈"
    STOP_MARKET = "STOP_MARKET"


class OptionType(Enum):
    """
    Option type.
    """
    CALL = "看涨期权"
    PUT = "看跌期权"


class Exchange(Enum):
    """
    Exchange.
    """
    BITMEX = "BITMEX"
    OKEX = "OKEX"
    HUOBI = "HUOBI"
    BITFINEX = "BITFINEX"
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"         # bybit.com
    COINBASE = "COINBASE"
    DERIBIT = "DERIBIT"
    GATEIO = "GATEIO"
    BITSTAMP = "BITSTAMP"
    DYDX = "DYDX"
    FTX = "FTX"
    RAYDIUNM = "RAYDIUNM"



class Currency(Enum):
    """
    Currency.
    """
    USD = "USD"
    HKD = "HKD"
    CNY = "CNY"


class Interval(Enum):
    """
    Interval of bar data.
    """
    MINUTE = "1m"
    HOUR = "1h"
    DAILY = "d"
    WEEKLY = "w"
    TICK = "tick"
    CUSTOM = 'custom'
