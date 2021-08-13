import re
from typing import Tuple

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

if __name__ == '__main__':
    ab_test = 'syx'
    check_ab_symbol(ab_test)