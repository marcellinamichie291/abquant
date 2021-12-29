
import argparse

from abquant.dataloader.dataloaderkline import DataLoaderKline
from abquant.dataloader.datasetkline import DatasetKline
from datetime import datetime


# 命令行参数的解析代码
def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--data_file', type=str, required=False,
                        help='Full path of data file you want to use')
    args = parser.parse_args()
    return args


def main():
    args = parse()

    dt_setting = {
        "data_file": args.data_file,
    }

    dataloader: DataLoaderKline = DataLoaderKline(dt_setting)
    dataset: DatasetKline = dataloader.load_data('ETHUSDT.BINANCE', datetime(2021, 12, 24), datetime(2021, 12, 28))
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
