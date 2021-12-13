
import argparse

from abquant.dataloader.dataloaderkline import DataLoaderKline
from abquant.dataloader.datasetkline import DatasetKline


# 命令行参数的解析代码
def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-x', '--exchange', type=str, required=False,
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

    dt_setting = {
        "exchange": args.exchange,
        "symbol": args.symbol,
        "trade_type": "bbc",    # spot, ubc, bbc
        "start_time": "2021-11-1",
        "end_time": "2021/12/15",
        "data_file": args.data_file,
        "interval": "1m",
    }

    dataloader: DataLoaderKline = DataLoaderKline(dt_setting)
    dataset: DatasetKline = dataloader.load_data()
    if dataset is None:
        return
    dataset.dataframe.info(memory_usage='deep')
    diter = iter(dataset)
    for d in diter:
        pass
    try:
        while True:
            dt = next(diter, None)
            if not dt:
                break
        for i in range(0, 10):
            d = next(diter)
            print(d)
    except Exception:
        newds = dataset.copy()
        newiter = iter(newds)
        for i in range(0, 10):
            d = next(newiter)
            print(d)


if __name__ == '__main__':
    main()
