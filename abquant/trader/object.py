
from dataclasses import dataclass
from datetime import datetime
from logging import INFO

from .common import Direction, Exchange, Interval, Offset, Status, Product, OptionType, OrderType
from .msg import BaseData, OrderData

@dataclass
class PositionData(BaseData):
    """
    仓位相关数据。
    """

    symbol: str
    exchange: Exchange
    direction: Direction

    volume: float = 0
    frozen: float = 0
    price: float = 0
    pnl: float = 0
    yd_volume: float = 0

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"
        self.ab_positionid = f"{self.ab_symbol}.{self.direction.value}"


@dataclass
class AccountData(BaseData):
    """
    账户相关数据。
    """

    accountid: str

    balance: float = 0
    frozen: float = 0

    def __post_init__(self):
        """"""
        self.available = self.balance - self.frozen
        self.ab_accountid = f"{self.gateway_name}.{self.accountid}"


@dataclass
class LogData(BaseData):
    """
    在需要相对低延迟的策略时， 需使用非同步阻塞文件写 ，可以用到的数据结构。
    """

    msg: str
    level: int = INFO

    def __post_init__(self):
        """"""
        self.time = datetime.now()


@dataclass
class ContractData(BaseData):
    """
    Contract data contains basic information about each contract traded.
    """

    symbol: str
    exchange: Exchange
    name: str
    product: Product
    size: float
    pricetick: float

    min_volume: float = 1           # minimum trading volume of the contract
    stop_supported: bool = False    # whether server supports stop order
    net_position: bool = False      # whether gateway uses net position volume
    history_data: bool = False      # whether gateway provides bar history data

    option_strike: float = 0
    option_underlying: str = ""     # ab_symbol of underlying contract
    option_type: OptionType = None
    option_expiry: datetime = None
    option_portfolio: str = ""
    option_index: str = ""          # for identifying options with same strike price

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"


# NOT SUPPORT YET 
@dataclass
class QuoteData(BaseData):
    """
    追踪双边挂单用。 通常用于做市策略，
    由于需交易所提供批挂批撤的api，短期内不打算实现。
    """

    symbol: str
    exchange: Exchange
    quoteid: str

    bid_price: float = 0.0
    bid_volume: int = 0
    ask_price: float = 0.0
    ask_volume: int = 0
    bid_offset: Offset = Offset.NONE
    ask_offset: Offset = Offset.NONE
    status: Status = Status.SUBMITTING
    datetime: datetime = None
    reference: str = ""

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"
        self.ab_quoteid = f"{self.gateway_name}.{self.quoteid}"
        raise NotImplemented(' for now this type {} is not support yet.'.format(self.__class__))

    def create_cancel_request(self) -> "CancelRequest":
        """
        Create cancel request object from quote.
        """
        req = CancelRequest(
            orderid=self.quoteid, symbol=self.symbol, exchange=self.exchange
        )
        return req


@dataclass
class SubscribeRequest:
    """
    订阅某交易所，的某金融产品的请求。
    """

    symbol: str
    exchange: Exchange

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"


@dataclass
class OrderRequest:
    """
    向某交易所发起某金融产品的交易单的请求。
    """

    symbol: str
    exchange: Exchange
    direction: Direction
    type: OrderType
    volume: float
    price: float = 0
    offset: Offset = Offset.NONE
    reference: str = ""

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"

    def create_order_data(self, orderid: str, gateway_name: str) -> OrderData:
        """
        给定orderid即 相应交易gateway，返回 OrderData对象。
        """
        order = OrderData(
            symbol=self.symbol,
            exchange=self.exchange,
            orderid=orderid,
            type=self.type,
            direction=self.direction,
            offset=self.offset,
            price=self.price,
            volume=self.volume,
            reference=self.reference,
            gateway_name=gateway_name,
        )
        return order


@dataclass
class CancelRequest:
    """
    取消某交易单的请求。
    """

    orderid: str
    symbol: str
    exchange: Exchange

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"


@dataclass
class HistoryRequest:
    """
    获取交易所历史k线数据的请求，通常用于实盘策略参数的初始化， 和分钟级别回测数据的抓取。
    """

    symbol: str
    exchange: Exchange
    start: datetime
    end: datetime = None
    interval: Interval = None

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"

# NOT SUPPORT YET 暂不支持！！
@dataclass
class QuoteRequest:
    """
    同上和QuoteData相类似， 未来可能会用于做市策略，暂不支持。
    """

    symbol: str
    exchange: Exchange
    bid_price: float
    bid_volume: int
    ask_price: float
    ask_volume: int
    bid_offset: Offset = Offset.NONE
    ask_offset: Offset = Offset.NONE
    reference: str = ""

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"
        raise NotImplemented(' for now this type {} is not support yet.'.format(self.__class__))

    def create_quote_data(self, quoteid: str, gateway_name: str) -> QuoteData:
        """
        Create quote data from request.
        """
        quote = QuoteData(
            symbol=self.symbol,
            exchange=self.exchange,
            quoteid=self.quoteid,
            bid_price=self.bid_price,
            bid_volume=self.bid_volume,
            ask_price=self.ask_price,
            ask_volume=self.ask_volume,
            bid_offset=self.bid_offset,
            ask_offset=self.ask_offset,
            reference=self.reference,
            gateway_name=gateway_name,
        )
        return quote
