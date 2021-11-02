import argparse
import time

from abquant.monitor import Monitor
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData


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
    monitor = Monitor(common_setting)
    monitor.start()

    i = 0
    while True:
        time.sleep(10)
        i += 1
        monitor.send(f'message {i}')


if __name__ == '__main__':
    main()
