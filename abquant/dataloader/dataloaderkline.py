
from typing import Dict
from datetime import datetime
import os

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
        self._logger = Logger("dataloader")
        self.exchange: Exchange = None
        self.symbol = None
        self.trade_type = None
        self.interval: Interval = None
        self.start_time: datetime = None
        self.end_time: datetime = None
        self.data_file = None
        self.data_location = None
        home_dir = os.environ['HOME']
        self.cache_dir = home_dir + '/.abquant/cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            self._logger.info(f'Data loader cache dir: {self.cache_dir}')
        # self.set_config(config)
        super().__init__(config)

    """
        config each item from setting dict
    """
    def set_config(self, setting):
        super().set_config(setting)
        if setting is None:
            self.data_location = DataLocation.REMOTE
            return
        """
            data_file has highest priority for data loader, if local data file is set, 
            dataloader will always load the specified data file firstly in LOCAL mode.
        """
        self.data_file = setting.get("data_file")
        if self.data_file is not None and os.path.isfile(self.data_file):
            self.data_location = DataLocation.LOCAL
        else:
            self.data_location = DataLocation.REMOTE

    def _clean_loader(self):
        self.exchange: Exchange = None
        self.symbol = None
        self.trade_type = None
        self.interval = None
        self.start_time = None
        self.end_time = None

    def _config_loader(self, ab_symbol: str, start: datetime, end: datetime, interval: Interval = Interval.MINUTE):
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
        if start is None or end is None:
            raise Exception(f'Dataloader config: neither start nor end time could be empty')
        # self.start_time = regular_time(start)
        # self.end_time = regular_time(end)
        self.start_time = start
        self.end_time = end
        if self.data_file is not None and os.path.isfile(self.data_file):
            self.data_location = DataLocation.LOCAL
        else:
            self.data_location = DataLocation.REMOTE

    """
        load csv data, local file or remote aws s3 files
    """
    def load_data(self, ab_symbol: str, start: datetime, end: datetime,
                  interval: Interval = Interval.MINUTE) -> Dataset:
        self._clean_loader()
        self._config_loader(ab_symbol, start, end, interval=interval)

        cache_file = ''
        intvl = '1m' if self.interval == Interval.MINUTE else '1m'

        # 检查缓存  todo: 数据合并
        if self.exchange is not None and self.symbol is not None and self.start_time is not None \
                and self.end_time is not None and self.trade_type is not None:
            stime = self.start_time.strftime('%Y-%m-%d')
            etime = self.end_time.strftime('%Y-%m-%d')
            cache_file = f"{self.exchange.value.lower()}-{self.symbol.lower()}-{self.trade_type}-{intvl}" \
                       f"-{stime}-{etime}.csv"
            if os.path.isfile(self.cache_dir + '/' + cache_file):
                # load from cache
                df_03 = pd.read_csv(self.cache_dir + '/' + cache_file, index_col=0)
                absymbol = generate_ab_symbol(self.symbol, self.exchange)
                dataset: DatasetKline = DatasetKline(self.start_time, self.end_time, absymbol, self.interval)
                dataset.set_data(df_03.to_dict(orient="records"), df_03, df_03.shape[0])
                self._logger.info(f"Load from cache: {self.cache_dir + '/' + cache_file}")
                return dataset

        df_01 = None
        df_02 = None
        if self.data_location == DataLocation.LOCAL:
            # path = Path(self.data_file)
            if self.data_file is not None and os.path.isfile(self.data_file):
                df_01 = pd.read_csv(self.data_file)
                df_02 = regular_df(df_01, self.exchange, self.symbol, intvl)
            else:
                return None

        elif self.data_location == DataLocation.REMOTE:
            loader = RemoteLoader(self.exchange, self.symbol, self.trade_type, self.interval,
                                  self.start_time, self.end_time)
            df_01 = loader.load_remote()
            df_02 = df_01

        if df_01 is None:
            self._logger.info('No data loaded, exit')
            return None
        self._logger.debug(df_01.head(1))

        rn, cn = df_02.shape
        if self.exchange is None:
            self.exchange = Exchange(df_02.iloc[0]['exchange'].upper())
        if self.symbol is None:
            self.symbol = df_02.iloc[0]['symbol']
        if self.start_time is None:
            self.start_time = datetime.strptime(str(df_02.iloc[0]['datetime']), '%Y-%m-%d %H:%M:%S')
        if self.end_time is None:
            self.end_time = datetime.strptime(str(df_02.iloc[rn - 1]['datetime']), '%Y-%m-%d %H:%M:%S')

        absymbol = generate_ab_symbol(self.symbol, self.exchange)
        dataset: DatasetKline = DatasetKline(self.start_time, self.end_time, absymbol, self.interval)

        dataset.set_data(df_02.to_dict(orient="records"), df_02, rn)

        # check
        if self.data_location == DataLocation.REMOTE:
            result = dataset.check()
            if not result:
                self._logger.info(f"Error: data check not pass, cannot load")
                return None

        # cache
        try:
            if cache_file is not None and len(cache_file) > 0:
                df_02.to_csv(self.cache_dir + '/' + cache_file)
            else:
                cache_file = f"{self.exchange.value.lower()}-{self.trade_type.lower()}-{self.symbol.lower()}-1m" \
                             f"-{str(self.start_time)[:19].replace(' ', '-')}-{str(self.end_time)[:19].replace(' ', '-')}.csv"
                df_02.to_csv(self.cache_dir + '/' + cache_file, index=False)

            self._logger.info(f"\n{'-'*32}\nLoaded k-line {self.interval.value} bars: {rn}\n{'-'*32}")
        except Exception as e:
            self._logger.error('Error saving cache: ', e)
        return dataset




