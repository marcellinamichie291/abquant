import os
from typing import Dict
from datetime import datetime

import pandas as pd

from abquant.trader.msg import Interval
from abquant.dataloader.dataloader import DataLoader, Dataset, DataLocation
from abquant.dataloader.datasetkline import DatasetKline
from abquant.dataloader.remoteloader import RemoteLoader
from abquant.dataloader.utility import regular_time, regular_df
from abquant.trader.utility import generate_ab_symbol, extract_ab_symbol
from abquant.trader.common import Exchange
from abquant.monitor.logger import Logger


class DataLoaderKline(DataLoader):
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self._logger = Logger("dataloader")
        home_dir = os.environ['HOME']
        self.cache_dir = home_dir + '/.abquant/cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            self._logger.info(f'Data loader cache dir: {self.cache_dir}')
        # self.set_config(config)

    def set_config(self, setting):
        super().set_config(setting)

    """
        load csv data, local file or remote aws s3 files
    """
    def load_data(self, ab_symbol: str, start: datetime, end: datetime,
                  interval: Interval = Interval.MINUTE) -> Dataset:
        return self._load_data(ab_symbol, start, end, interval=interval)

    def load_local_data(self, ab_symbol: str, start: datetime, end: datetime,
                  interval: Interval = Interval.MINUTE, data_file: str = None) -> Dataset:
        return self._load_data(ab_symbol, start, end, interval=interval, data_file=data_file)

    def _load_data(self, ab_symbol: str, start: datetime, end: datetime,
                  interval: Interval = Interval.MINUTE, data_file: str = None) -> Dataset:
        loader = LoaderKline()
        loader.config_loader(ab_symbol, start, end, interval=interval, data_file=data_file)

        intvl = '1m' if loader.interval == Interval.MINUTE else '1m'
        stime = loader.start_time.strftime('%Y-%m-%d')
        etime = loader.end_time.strftime('%Y-%m-%d')
        cache_file = f"{loader.exchange.value.lower()}-{loader.trade_type.lower()}-{loader.symbol.lower()}-{intvl}" \
                     f"-{stime}-{etime}.csv"

        # 检查缓存  todo: 数据合并
        if os.path.isfile(self.cache_dir + '/' + cache_file):
            # load from cache
            df_03 = pd.read_csv(self.cache_dir + '/' + cache_file, index_col=0)
            absymbol = generate_ab_symbol(loader.symbol, loader.exchange)
            dataset: DatasetKline = DatasetKline(loader.start_time, loader.end_time, absymbol, loader.interval)
            dataset.set_data(df_03.to_dict(orient="records"), df_03, df_03.shape[0])
            self._logger.info(f"Load from cache: {self.cache_dir + '/' + cache_file}")
            return dataset

        df_01 = None
        df_02 = None
        if loader.data_location == DataLocation.LOCAL:
            if loader.data_file is not None and os.path.isfile(loader.data_file):
                df_01 = pd.read_csv(loader.data_file)
                df_02 = regular_df(df_01, loader.exchange, loader.symbol.upper(), intvl)
            else:
                return None

        elif loader.data_location == DataLocation.REMOTE:
            loader = RemoteLoader(loader.exchange, loader.symbol, loader.trade_type, loader.interval,
                                  loader.start_time, loader.end_time)
            df_01 = loader.load_remote()
            df_02 = df_01

        if df_01 is None:
            self._logger.info('No data loaded, exit')
            return None
        self._logger.debug(df_01.head(1))

        rn, cn = df_02.shape
        if loader.exchange is None:
            loader.exchange = Exchange(df_02.iloc[0]['exchange'].upper())
        if loader.symbol is None:
            loader.symbol = df_02.iloc[0]['symbol']
        if loader.start_time is None:
            loader.start_time = datetime.strptime(str(df_02.iloc[0]['datetime']), '%Y-%m-%d %H:%M:%S')
        if loader.end_time is None:
            loader.end_time = datetime.strptime(str(df_02.iloc[rn - 1]['datetime']), '%Y-%m-%d %H:%M:%S')

        absymbol = generate_ab_symbol(loader.symbol, loader.exchange)
        dataset: DatasetKline = DatasetKline(loader.start_time, loader.end_time, absymbol, loader.interval)
        dataset.set_data(df_02.to_dict(orient="records"), df_02, rn)

        # check
        if loader.data_location == DataLocation.REMOTE:
            result = dataset.check()
            if not result:
                self._logger.info(f"Error: data check not pass, cannot load")
                return None

        # cache
        try:
            if cache_file is not None and len(cache_file) > 0:
                df_02.to_csv(self.cache_dir + '/' + cache_file)
            else:
                df_02.to_csv(self.cache_dir + '/' + cache_file, index=False)

            self._logger.info(f"\n{'-'*32}\nLoaded k-line {loader.interval.value} bars: {rn}\n{'-'*32}")
        except Exception as e:
            self._logger.error('Error saving cache: ', e)
        return dataset


class LoaderKline:
    def __init__(self):
        self.exchange: Exchange = None
        self.symbol = None
        self.trade_type = None
        self.interval: Interval = None
        self.start_time: datetime = None
        self.end_time: datetime = None
        self.data_file = None
        self.data_location = None

    def config_loader(self, ab_symbol: str, start: datetime, end: datetime,
                      interval: Interval = Interval.MINUTE, data_file: str = None):
        if data_file is not None and os.path.isfile(data_file):
            self.data_file = data_file
            self.data_location = DataLocation.LOCAL
        else:
            self.data_location = DataLocation.REMOTE
        if ab_symbol is None:
            raise Exception(f'Dataloader: ab_symbol is none')
        symbol, exchange = extract_ab_symbol(ab_symbol)
        if exchange is None:
            raise Exception(f'Dataloader: exchange is none')
        self.exchange = exchange
        self.symbol = symbol
        if self.symbol is None:
            raise Exception(f'Dataloader: symbol is none')
        self.symbol = self.symbol.strip("'\" \n\t")
        if self.exchange == Exchange.BINANCE:
            if self.symbol.islower():
                self.trade_type = 'spot'
            elif 'USDT' in self.symbol or 'BUSD' in self.symbol:
                self.trade_type = 'ubc'
            elif 'USD_' in self.symbol:
                self.trade_type = 'bbc'
            else:
                raise Exception(f'Dataloader: ambiguous symbol for sub trading account type')
        if interval != Interval.MINUTE:
            raise Exception(f'Dataloader config: only accept interval MINUTE, but set: {interval}')
        self.interval = interval
        if start is None or end is None:
            raise Exception(f'Dataloader config: neither start nor end time could be empty')
        # self.start_time = regular_time(start)
        # self.end_time = regular_time(end)
        self.start_time = start
        self.end_time = end


