
from dataclasses import dataclass
from datetime import datetime
from logging import INFO, currentframe
from time import localtime
from typing import List, Optional

from .common import Direction, Exchange, Interval, Offset, Status, Product, OptionType, OrderType

ACTIVE_STATUSES = {Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED}


@dataclass
class BaseData:
    gateway_name: str


@dataclass
class TickData(BaseData):
    '''
    tick原本的含义是最优ask bid的price 以及volume的 real-time更新。
    但由于
    1. 方便一些需要盘口周围小范围orderbook深度的策略编写
    2. 回测易于实现的原因。
    3. 部分币所提供的接口存在特殊性（binance提供 real-time的ticker和 100ms-1000ms延时的depth）
    初期TickData这个数据会承载3个功能---即三种事件发生时会生成：
    1. 最优ask，bid更新，分属字段best_{ask}/{bid}_{price}/{volumn}，当交易所发包最优ticker时。
    2. 成交发生时，分属字段trade_price, trade_volume,才会更新。订单流相关策略可以监控这两个字段, 同时，部分交易所仅在成交发生时更新timestamp，需要注意。
    3. 最优5档ask，bid更新， 分属字段 {ask}/{bid}_price_{1-5}, {ask}/{bid}_volume_{1-5}, 
    注意最优五档ask，bid和 最优best ask，bid，由于交易所提供api有可能存在不同延时，有可能不兼容, 且由于timestamp机制比较诡异+延迟不同，
    根据depth信息推导best ask bid很可能存在错误。（
    例如binance的深度信息存在100ms+延迟，而ticker则为real-time stream。而bitmex总体都是实时。）
    '''
    symbol: str
    exchange: Exchange
    # 有些币所的特点是，发生成交的数据包才会返回时间戳，因此该字段变动，即意味着发生了taker成交。
    datetime: datetime


    # 当发生交易，该字段有值。 可以根据该组字段判断tick来接收 市场中的成交信息。
    trade_price: float = 0
    trade_volume: float = 0

    # 有些币所得最优 bid/ask 数据realtime，而深度数据并不实时，因此bid/ask_price_1字段有可能与该字段不一致。
    best_ask_price: float = 0
    best_ask_volume: float = 0
    best_bid_price: float = 0
    best_bid_volume: float = 0

    # 最优5档，（会根据交易所提供的接口，选择实时成都最高的方式更新，有可能是根据委托单也有可能使用交易所提供的depth，）。
    bid_price_1: float = 0
    bid_price_2: float = 0
    bid_price_3: float = 0
    bid_price_4: float = 0
    bid_price_5: float = 0

    ask_price_1: float = 0
    ask_price_2: float = 0
    ask_price_3: float = 0
    ask_price_4: float = 0
    ask_price_5: float = 0

    bid_volume_1: float = 0
    bid_volume_2: float = 0
    bid_volume_3: float = 0
    bid_volume_4: float = 0
    bid_volume_5: float = 0

    ask_volume_1: float = 0
    ask_volume_2: float = 0
    ask_volume_3: float = 0
    ask_volume_4: float = 0
    ask_volume_5: float = 0

    # 收到该事件时候，本地时戳
    localtime: datetime = None

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"


@dataclass
class BarData(BaseData):
    ''''
    k线数据，通常通过BarGenerator根据TickData生成，而非订阅交易所K线。
    原因有2：
    1. 由于不是所有交易所都支持实时更新K线数据（有些交易所不支持订阅k线，
    而是通过，query—history的方式获得历史，因此不支持事件的方式返回Bar数据） 
    2. 回测实现难度。

    具体如何根据tick生成bar，可以参考example中的实现，和BarGenerator，
    比起直接使用诸如 binance的kline 协议，并不会增加超过3行以上代码的使用难度，
    且增加了大量的灵活性---支持生成个性化时间间隔的OCHLV数据，ms至月，任意interval皆可支持。
    '''
    symbol: str
    exchange: Exchange
    datetime: datetime

    interval: Interval = None
    volume: float = 0
    # open_interest: float = 0
    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    close_price: float = 0

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"


@dataclass
class TransactionData(BaseData):
    '''
    交易所成交 交易单数据。可用于给予订单生成因子的策略。
    会在实盘中支持相应回调接口。
    但由于回测时支持该接口较为困难， 可能会在较后版本才能支持，建议使用TickData中 datetime变更的机制，
    根据 last_price, last_volumn获取交易所成交信息.

    '''

    symbol: str
    exchange: Exchange
    datetime: datetime

    volume: float = 0
    price: float = 0

    # 部分交易所可能公示 交易双方的id。该字段在一些特殊的需重建orderbook的策略中可能有用。
    bid_no: int = 0 
    ask_no: int = 0
    times: int = 0
    # taker 成交的方向
    direction: Direction = None

    # 收到该事件时候，本地时戳
    localtime: datetime = None

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"


# Not Supproted yet
@dataclass
class EntrustData(BaseData):
    '''
    交易所交易单广播数据。
    仅有部分交易所可能支持。该数据可用于特殊策略 重建orderbook的需求。
    由于支持的交易所较少，且难于实现相应的回测。
    暂时不支持
    '''

    symbol: str
    exchange: Exchange
    datetime: datetime

    volume: float = 0
    price: float = 0

    # 委托交易单的交易者id， 可能会有交易所提供
    entrust_no: int = 0 

    direction: Direction = None
    order_type: OrderType = OrderType.LIMIT
    localtime: datetime = None


    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"
        raise NotImplemented(' for now this type {} is not support yet.'.format(self.__class__))


@dataclass
class DepthData(BaseData):
    '''
    大部分交易所支持的，orderbook深度更新。
    该数据可用于特殊策略 重建orderbook的需求。
    但部分交易所的更新并非实时，延迟从30ms--100ms， 深度从25档--400档都有可能， abquant会尽可能选择实时更新wss接口。
    但回测支持较为困难， 初期该数据结构结构会用于更新 TickData内的最优5档。 
    交易者最好不要使用。 
    '''

    symbol: str
    exchange: Exchange
    datetime: datetime

    ask_volumes: List[float] = None
    ask_prices: List[float] = None
    bid_volumes: List[float] = None
    bid_prices: List[float] = None

    times: int = 0
    localtime: datetime = None

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"



@dataclass
class OrderData(BaseData):
    '''
    个人交易单状态更新时，需处理该数据结构。
    OrderData表示， 在某交易所所下交易单有状态改变。
    状态改变分别有： 
    SUBMITTING = "提交中" 交易单单刚提交后返回
    NOTTRADED = "未成交"  limit order，提交到交易所，交易所挂单成功时返回
    PARTTRADED = "部分成交" ， limit order 部分成交时返回。
    ALLTRADED = "全部成交"  limiter order taker 全部成交时返回。
    CANCELLED = "已撤销"  cancelorder发出， 交易所成功撤销订单后，返回
    REJECTED = "拒单"  通常发生在spam ban， 交易单单价格超过合理值，交易单单量低于阈值等等情况

    '''
    symbol: str
    exchange: Exchange
    orderid: str
    # 订单类型，limit， market， stoploss 等等，后续可以逐步扩展
    type: OrderType = OrderType.LIMIT
    direction: Direction = None
    # 开平仓， 存在部分交易所仅有净头寸 不存在开平仓的概念， 交易员可以不用在意该字段。
    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    # 已成交
    traded: float = 0
    # 交易单状态
    status: Status = Status.SUBMITTING
    datetime: datetime = None
    reference: str = ""

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"
        self.ab_orderid = f"{self.gateway_name}.{self.orderid}"

    def is_active(self) -> bool:
        """
        """
        if self.status in ACTIVE_STATUSES:
            return True
        else:
            return False

    def create_cancel_request(self) -> "CancelRequest":
        """
        """
        # deal with circle import 
        from .object import CancelRequest
        req = CancelRequest(
            orderid=self.orderid, symbol=self.symbol, exchange=self.exchange
        )
        return req


@dataclass
class TradeData(BaseData):
    """
    个人某交易单存在成交，或部分成交时，需处理该数据结构。
    TradeData表示，在某交易所所挂交易单有成交发生。
    """

    symbol: str
    exchange: Exchange
    # 关联的交易单id
    orderid: str
    tradeid: str
    # 成交方向
    direction: Direction = None
    # 开/平仓
    offset: Offset = Offset.NONE
    # 已什么价格成交， limit order，maker成交时为定值， limit order taker成交或，market order成交时，
    # 根据交易所的实现，有可能分批返回不同的成交价格，也可能返回单次的平均成交价格。
    price: float = 0
    # 当前次成交量。
    volume: float = 0
    datetime: datetime = None

    def __post_init__(self):
        """"""
        self.ab_symbol = f"{self.symbol}.{self.exchange.value}"
        self.ab_orderid = f"{self.gateway_name}.{self.orderid}"
        self.ab_tradeid = f"{self.gateway_name}.{self.tradeid}"

