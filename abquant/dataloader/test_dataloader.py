from datetime import datetime
import argparse

from abquant.monitor import Monitor
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.dataloader.dataloaderkline import DataLoaderKline
from abquant.dataloader.datasetkline import DatasetKline


# 命令行参数的解析代码，交易员可以不用懂。
def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-x', '--exchange', type=str, required=True,
                        help='Exchange that backtest data is from')
    parser.add_argument('-y', '--symbol', type=str, required=False,
                        help='Coin pair symbol name, no slash, eg. BTCUSDT')
    parser.add_argument('-s', '--start_time', type=str, required=False,
                        help='Start time of the backtest data')
    parser.add_argument('-e', '--end_time', type=str, required=False,
                        help='End time of the backtest data')
    parser.add_argument('-f', '--data_file', type=str, required=False,
                        help='Full dir of your own data file')
    args = parser.parse_args()
    return args


def main():
    args = parse()

    common_setting = {
        "strategy": "grid",
        "lark_url": None,  # "https://open.larksuite.com/open-apis/bot/v2/hook/2b92f893-83c2-48c1-b366-2e6e38a09efe",
        "log_path": None,
    }

    dt_setting = {
        "exchange": args.exchange,
        "symbol": args.symbol,
        "trade_type": "spot",
        "start_time": "2021-11-20 00:00:00",
        "end_time": "2021-11-26 00:00:00",
        "location": "local",
        "data_file": args.data_file,
        "interval": "1m",
    }
    # 初始化 monitor
    # monitor = Monitor(common_setting)
    # monitor.start()

    dataloader: DataLoaderKline = DataLoaderKline(dt_setting)
    dataset: DatasetKline = dataloader.load_data()
    diter = iter(dataset)
    for i in range(0, 10):
        d = next(diter)
        print(d)


if __name__ == '__main__':
    main()
    # test()
