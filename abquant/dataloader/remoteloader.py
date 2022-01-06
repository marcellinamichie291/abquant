
from datetime import datetime, timedelta
import os
import pandas as pd
import gzip
from pandas.core.frame import DataFrame
import threading
import boto3

from abquant.trader.common import Exchange
from abquant.dataloader.utility import regular_df
from abquant.monitor.logger import Logger
from abquant.trader.msg import Interval

# s3 config
S3_BUCKET_NAME = "abquant-binance-data"
S3_HOME_FOLDER = ""
LOCAL_PATH = os.environ['HOME'] + '/.abquant/data/aws/kline'
AWS_S3_BASE_PATH = "s3://" + S3_BUCKET_NAME + S3_HOME_FOLDER


class RemoteLoader:
    def __init__(self, exchange: Exchange, symbol, trade_type, interval, start_time: datetime, end_time: datetime):
        self._logger = Logger("dataloader")
        self.exchange: Exchange = exchange
        self.symbol = symbol
        self.trade_type = trade_type
        self.interval: Interval = interval
        self.start_time: datetime = start_time
        self.end_time: datetime = end_time
        self.data_location = None
        self._s3 = boto3.resource('s3')
        self._bucket = self._s3.Bucket(S3_BUCKET_NAME)
        self._rlock = threading.RLock()
        if not os.path.exists(LOCAL_PATH):
            try:
                os.makedirs(LOCAL_PATH)
            except Exception:
                self._logger.error(f'Cannot create s3 data dir: {LOCAL_PATH}, exit')
                return

    def gunzip_file(self, file_name):
        # 获取文件的名称，去掉后缀名
        f_name = file_name.replace(".gz", "")
        if os.path.isfile(f_name):   # 文件存在（已解压），则退出
            self._logger.info("file has been unziped, omit.")
            return f_name
        # 开始解压
        g_file = gzip.GzipFile(file_name)
        # 读取解压后的文件，并写入去掉后缀名的同名文件（即得到解压后的文件）
        open(f_name, "wb+").write(g_file.read())
        self._logger.debug("unzip: " + f_name)
        g_file.close()
        return f_name

    def load_file(self, local_dir, file_base) -> DataFrame:
        if os.path.isdir(local_dir):
            basefile = os.path.join(local_dir, file_base)
            gzfile = os.path.join(local_dir, file_base + '.gz')
            csvfile = os.path.join(local_dir, file_base + '.csv')
            if not os.path.isfile(basefile) and not os.path.isfile(csvfile) and os.path.isfile(gzfile):
                filename = self.gunzip_file(gzfile)
                if filename[-4:] != '.csv':
                    filename += '.csv'
            if os.path.isfile(basefile):
                os.rename(basefile, csvfile)
            elif not os.path.isfile(csvfile):
                return None
            df_file = pd.read_csv(csvfile, encoding="utf8", sep=',', dtype=None)
            self._logger.debug(df_file.shape)
            rows, cols = df_file.shape
            if rows > 0:
                return df_file
            else:
                raise Exception("No record found.")
        else:
            self._logger.info(f"Directory not exist: {local_dir}")
            return None

    def load_remote(self):
        try:
            intvl = '1m' if self.interval == Interval.MINUTE else '1m'
            prefix = f'{self.exchange.value.lower()}/{self.trade_type}/daily/{self.symbol.upper()}/{intvl}/'
            sub_dir = '/' + prefix
            enday = self.end_time.strftime('%Y-%m-%d')
            file_name = f'{self.symbol.upper()}-{intvl}-{enday}.csv'
            remote_dir = AWS_S3_BASE_PATH + sub_dir
            local_dir = LOCAL_PATH + sub_dir
            local_file = LOCAL_PATH + sub_dir + file_name
        except Exception as e:
            self._logger.error(e)
            self._logger.error('Short of parameters, cannot specify local s3 file')

        try:
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            dated = self.start_time
            selected_days = []
            while dated < self.end_time:
                enday = dated.strftime('%Y-%m-%d')
                selected_days.append(enday)
                dated = dated + timedelta(days=1)
            self._rlock.acquire()
            n = 0
            try:
                for obj in self._bucket.objects.filter(Prefix=prefix):
                    ofile = LOCAL_PATH + '/' + obj.key
                    oname = os.path.basename(obj.key)
                    if oname == '' or '.' not in oname or intvl not in oname:
                        continue
                    odate = oname.split('.')[0].split(intvl)[1].strip('-')
                    if odate in selected_days and oname[-3:] == 'csv' and not os.path.isfile(ofile):
                        if n == 0:
                            self._logger.info(f'syncing {remote_dir} to {local_dir} ...')
                        self._logger.info(
                            threading.current_thread().name + f' downloading {AWS_S3_BASE_PATH + obj.key} to {ofile} ...')
                        self._bucket.download_file(obj.key, ofile)
                        n += 1
                if n > 0:
                    self._logger.info('sync over' + f', {n} downloaded' if n > 0 else '')
            finally:
                self._rlock.release()
        except Exception as e:
            self._logger.error("Error when syncing s3 files:")
            self._logger.error(e)
            raise e

        try:
            if self.start_time >= self.end_time:
                raise AttributeError('start time is later than end time')
            dateday = self.start_time
            df_all = None
            days = 0
            short_days = []
            while dateday < self.end_time:
                enday = dateday.strftime('%Y-%m-%d')
                file_base = f'{self.symbol.upper()}-{intvl}-{enday}'
                file_name = f'{file_base}.csv'
                df1 = self.load_file(local_dir, file_base)
                dateday = dateday + timedelta(days=1)
                days += 1
                df1 = regular_df(df1, self.exchange, self.symbol.upper(), intvl)
                if df1 is None:
                    short_days.append(enday)
                    continue
                self._logger.debug(df1.shape)
                if df_all is None:
                    df_all = df1
                else:
                    df_all = df_all.append(df1)    # todo: 去重
            self._logger.info(f'Searching {days} days, {len(short_days)} days not available'
                              f'{": " + str(short_days[:10]) if len(short_days) > 0 else ""}'
                              f'{" ..." if len(short_days) > 10 else ""}')
            return df_all
        except Exception as e:
            self._logger.error(e)
            raise e


if __name__ == '__main__':
    loader = RemoteLoader(Exchange.BINANCE, 'ETHUSDT', 'spot', '1m',
                          datetime(2021, 6, 20, 16, 46, 19, 100127),
                          datetime(2021, 12, 1, 16, 46, 19, 100127))
    pdf = loader.load_remote()
    if pdf is not None and not pdf.empty:
        print(pdf[:3])
