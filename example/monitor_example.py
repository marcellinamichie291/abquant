import argparse
from datetime import datetime
import time

from abquant.monitor import Monitor
from abquant.trader.common import Direction, Exchange, Offset, OrderType, Status
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import LogData






def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--username', type=str, required=True,
                        help='username')
    parser.add_argument('-w', '--password', type=str, required=True,
                        help='password')
    args = parser.parse_args()
    return args

def main():
    args = parse()
    common_setting = {
        "username": args.username,
        "password": args.password,
    }
    # Monitor.init_monitor(common_setting)
    monitor = Monitor(common_setting)
    monitor.start()


    while True:
        time.sleep(5)
        order = OrderData('binancec', 'BTCUSDT', Exchange.BINANCE, '123123123213', OrderType.LIMIT, Direction.LONG, Offset.CLOSE, 100, 100, 1, Status.ALLTRADED, datetime.now())
        monitor.send_order("strategy-123123", order)
        trade = TradeData('binancec', 'BTCUSDT', Exchange.BINANCE, 'asdfasdf', 'asdfsdf2322', Direction.LONG, Offset.OPEN, 112, 222, datetime.now())
        monitor.send_trade('strategy-123123', trade)

        monitor.send_position('strategy-123123', ab_symbol="BTCUSDT.BINANCE", pos=1.1)
        monitor.send_parameter('strategy-123123', {'a': 1, 'b': 2})
        monitor.send_variable('strategy-123123', {'a': 1, 'b': [1,1,1]})
        monitor.send_log('strategy-123123', LogData('binancec', 'ahahaahahah'))


if __name__ == '__main__':
    main()
