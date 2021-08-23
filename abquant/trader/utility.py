import re
from typing import Tuple, Dict
import logging
from threading import Lock

from .common import Exchange

ab_symbol_parrtern= re.compile(r'(.*)\.(.*)')

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



def extract_vt_symbol(ab_symbol: str) -> Tuple[str, Exchange]:
    """
    :return: (symbol, exchange)
    """
    symbol, exchange_name = ab_symbol.split(".")
    return symbol, Exchange(exchange_name)


def generate_vt_symbol(symbol: str, exchange: Exchange) -> str:
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


if __name__ == '__main__':
    ab_test = 'syx'
    print(ab_test)
    check_ab_symbol(ab_test)

    get_file_logger('haha')