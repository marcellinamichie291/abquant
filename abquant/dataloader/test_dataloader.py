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
    parser.add_argument('-k', '--aws_access_key_id', type=str, required=False,
                        help='s3 aws_access_key_id')
    parser.add_argument('-s', '--aws_secret_access_key', type=str, required=False,
                        help='s3 aws_secret_access_key')
    args = parser.parse_args()
    return args


def main():
    args = parse()

    setting = {
        "aws_access_key_id": args.aws_access_key_id,
        "aws_secret_access_key": args.aws_secret_access_key,
    }

    dataloader: DataLoaderKline = DataLoaderKline(setting)
    for i in range(1, 2):
        threading.Thread(name='thread-'+str(i), target=load_data, args=(dataloader, i, args.data_file)).start()


def load_data(dataloader, day, data_file):
    print(threading.current_thread().name + ': start --------------')
    dataset: DatasetKline = dataloader.load_data('BTCUSDT.BINANCE',
                                                 datetime(2021, 12, day, 9), datetime(2021, 12, 5, 12))
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
