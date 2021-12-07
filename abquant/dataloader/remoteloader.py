
from datetime import datetime, timedelta
import os
import pandas as pd
import gzip
from pandas.core.frame import DataFrame

from abquant.trader.common import Exchange
from abquant.trader.msg import Interval
from abquant.dataloader.utility import regular_df

# s3 config
S3_BUCKET_NAME = "abquant-binance-data"
S3_HOME_FOLDER = "/"
LOCAL_PATH = "/data/aws/kline"
AWS_S3_BASE_PATH = "s3://" + S3_BUCKET_NAME + S3_HOME_FOLDER


class RemoteLoader:
    def __init__(self, exchange: Exchange, symbol, trade_type, interval, start_time: datetime, end_time: datetime):
        self.exchange: Exchange = exchange
        self.symbol = symbol
        self.trade_type = trade_type
        self.interval = interval
        self.start_time = start_time
        self.end_time = end_time
        self.data_location = None
        if not os.path.exists(LOCAL_PATH):
            try:
                os.makedirs(LOCAL_PATH)
            except Exception:
                print(f'Cannot create s3 data dir: {LOCAL_PATH}, exit')
                return

    def gunzip_file(self, file_name):
        # 获取文件的名称，去掉后缀名
        f_name = file_name.replace(".gz", "")
        if os.path.isfile(f_name):   # 文件存在（已解压），则退出
            print("file has been unziped, omit.")
            return f_name
        # 开始解压
        g_file = gzip.GzipFile(file_name)
        # 读取解压后的文件，并写入去掉后缀名的同名文件（即得到解压后的文件）
        open(f_name, "wb+").write(g_file.read())
        print("unzip: " + f_name)
        g_file.close()
        return f_name

    def load_file(self, local_dir, file_base) -> DataFrame:
        if os.path.isdir(local_dir):
            basefile = os.path.join(local_dir, file_base)
            gzfile = os.path.join(local_dir, file_base + '.gz')
            csvfile = os.path.join(local_dir, file_base + '.csv')
            if not os.path.isfile(basefile) and not os.path.isfile(csvfile) and os.path.isfile(gzfile):
                filename = self.gunzip_file(gzfile)
                print("unzip: " + filename)
                if filename[-4:] != '.csv':
                    filename += '.csv'
            if os.path.isfile(basefile):
                os.rename(basefile, csvfile)
            elif not os.path.isfile(csvfile):
                return None
            df_file = pd.read_csv(csvfile, encoding="utf8", sep=',', dtype=None)
            print(df_file.shape)
            rows, cols = df_file.shape
            if rows > 0:
                return df_file
            else:
                raise Exception("No record found.")
        else:
            print(f"Directory not exist: {local_dir}")
            return None

    def load_remote(self):
        remote_dir = ''
        local_dir = ''

        if not os.path.isfile(os.path.join(local_dir, "_SUCCESS")):
            cmd = "aws s3 sync " + AWS_S3_BASE_PATH + " " + LOCAL_PATH
            ret = os.system(cmd)
            if ret != 0:
                raise Exception('Sync AWS S3 failure: command=%s, status=%s' % (cmd, ret))
            else:
                print("sync success!")

        try:
            if self.start_time >= self.end_time:
                raise AttributeError('start time is later than end time')
            dateday = self.start_time
            df_all = None
            days = 0
            while dateday <= self.end_time:
                # local_dir = LOCAL_PATH + '/' + self.exchange.value.lower() + "/" + self.symbol + "/"
                local_dir = LOCAL_PATH
                file_base = self.symbol + '-' + self.interval + '-' + dateday.strftime('%Y-%m-%d')
                df1 = self.load_file(local_dir, file_base)
                dateday = dateday + timedelta(days=1)
                days += 1
                df1 = regular_df(df1, self.exchange, self.symbol, self.interval)
                if df1 is None:
                    continue
                print(df1.shape)
                if df_all is None:
                    df_all = df1
                else:
                    df_all = df_all.append(df1)    # todo: 去重
            return df_all
        except Exception as e:
            print(e)
            raise e


if __name__ == '__main__':
    loader = RemoteLoader(Exchange.BINANCE, 'BTCUSDT', 'spot', '1m',
                          datetime(2021, 6, 20, 16, 46, 19, 100127),
                          datetime(2021, 12, 1, 16, 46, 19, 100127))
    pdf = loader.load_remote()
    print(pdf[:3])
