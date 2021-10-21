from logging import WARNING
from abquant.gateway import accessor
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


class DydxWebsocketListener(WebsocketListener):
    """
    dydx websocket，
    委托、资金、持仓
    
    """
