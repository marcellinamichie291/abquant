from collections import defaultdict
from datetime import datetime
from enum import Enum
import re
from typing import Iterable, List, Tuple, Dict
import logging
from threading import Lock
from decimal import Decimal
import math
import inspect

from abquant.trader.msg import OrderData

from .common import Exchange

ab_symbol_parrtern = re.compile(r'(.*)\.(.*)')


def check_ab_symbol(ab_symbol: str) -> bool:
    '''
    chekc if a ab symbol valied
    '''
    match = ab_symbol_parrtern.fullmatch(ab_symbol)
    if match:
        symbol_name, exchange_name = match.groups()
        try:
            # checkout symbol_name
            Exchange(exchange_name)
        except ValueError as e:
            return False

        return True
    else:

        return False


def extract_ab_symbol(ab_symbol: str) -> Tuple[str, Exchange]:
    """
    :return: (symbol, exchange)
    """
    symbol, exchange_name = ab_symbol.split(".")
    return symbol, Exchange(exchange_name)


def generate_ab_symbol(symbol: str, exchange: Exchange) -> str:
    """
    return ab_symbol
    """
    return f"{symbol}.{exchange.value}"


file_handlers: Dict[str, logging.FileHandler] = {}

log_formatter = logging.Formatter('[%(asctime)s] %(message)s')

handler_mutex = Lock()


def _get_file_logger_handler(filename: str) -> logging.FileHandler:
    handler = file_handlers.get(filename, None)
    if handler is None:
        with handler_mutex:
            handler = file_handlers.get(filename, None)
            if handler is None:
                handler = logging.FileHandler(filename)
            file_handlers[filename] = handler
    return handler


def get_file_logger(filename: str) -> logging.Logger:
    logger = logging.getLogger(filename)
    handler = _get_file_logger_handler(filename)
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)
    return logger


def round_to(value: float, target: float) -> float:
    value = Decimal(str(value))
    target = Decimal(str(target))
    rounded = float(int(round(value / target)) * target)
    return rounded


def round_up(value: float, target: float) -> float:
    value = Decimal(str(value))
    target = Decimal(str(target))
    rounded = float(int(math.ceil(value / target)) * target)
    return rounded


def round_down(value: float, target: float) -> float:
    value = Decimal(str(value))
    target = Decimal(str(target))
    rounded = float(int(math.floor(value / target)) * target)
    return rounded


def object_as_dict(obj):
    d = {}
    for attr in dir(obj):
        if not attr.startswith('__'):
            try:
                value = getattr(obj, attr)
                if isinstance(value, Enum):
                    d[attr] = value.name
                    continue
                if isinstance(value, datetime):
                    d[attr] = value.timestamp()
                    continue
                if not inspect.ismethod(value):
                    d[attr] = value
            except UnicodeDecodeError:
                continue
    return d

class OrderGrouper:
    def __init__(self):
        self.gateway_name_orders_map: Dict[str: List[OrderData]] = defaultdict(list)

    def add(self, order: OrderData) -> None:
        self.gateway_name_orders_map[order.gateway_name].append(order)
    
    def get(self, gateway_name: str) -> Dict[str, List[OrderData]] :
        return self.gateway_name_orders_map[gateway_name]
    
    def __getitem__(self, gateway_name: str) -> List[OrderData]:
        return self.gateway_name_orders_map[gateway_name]
    
    def items(self) -> Iterable[Tuple[str, List[OrderData]]]:
        return self.gateway_name_orders_map.items()


if __name__ == '__main__':
    ab_test = 'syx'
    print(ab_test)
    check_ab_symbol(ab_test)

    get_file_logger('haha')

    grouper = OrderGrouper()
    grouper.add(OrderData(gateway_name='A', symbol='a', exchange=Exchange.BINANCE, orderid='1'))
    grouper.add(OrderData(gateway_name='A', symbol='b', exchange=Exchange.BINANCE, orderid='2'))
    grouper.add(OrderData(gateway_name='B', symbol='a', exchange=Exchange.BINANCE, orderid='3'))
    for name, order in grouper.items():
        print(name, order)
