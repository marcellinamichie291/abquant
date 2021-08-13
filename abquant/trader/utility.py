import re

ab_symbol_parrtern= re.compile(r'(.*)\.(.*)')

def check_ab_symbol(ab_symbol: str) -> bool:
    # chekc if a ab symbol valied
    match = ab_symbol_parrtern.fullmatch(ab_symbol)
    if match:
        symbol_name, exchange_name = match.groups()
        # checkout symbol_name
        print(symbol_name, exchange_name)
        # cehckout exchange_name
        return True
    else:
        return False


class BarGenerator:
    def __init__(self, interval):
        pass

if __name__ == '__main__':
    ab_test = 'syx'
    check_ab_symbol(ab_test)