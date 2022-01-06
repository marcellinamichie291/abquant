import argparse
import threading

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
    }

    dataloader: DataLoaderKline = DataLoaderKline(dt_setting)
    for i in range(10, 14):
        threading.Thread(name='thread-'+str(i-9), target=load_data, args=(dataloader, i, args.data_file)).start()


def load_data(dataloader, day, data_file):
    print(threading.current_thread().name + ': start --------------')
    dataset: DatasetKline = dataloader.load_data('ethusdt.BINANCE', datetime(2021, 11, day), datetime(2021, 11, 15),
                                                 data_file=data_file)
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
    ds2 = dataset.copy()
    n = 0
    for d in ds2:
        print(d)
        n += 1
        if n > 10:
            break
    print(threading.current_thread().name + ': end <<<<<<<<<<<<')


if __name__ == '__main__':
    main()
