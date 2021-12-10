
from typing import Dict, Iterable
from datetime import datetime
import os

import pandas as pd
from pandas.core.frame import DataFrame
from pathlib import Path

from abquant.trader.msg import Interval
from abquant.dataloader.dataloader import DataLoader, Dataset, DataLocation
from abquant.dataloader.datasetkline import DatasetKline
from abquant.dataloader.remoteloader import RemoteLoader
from abquant.dataloader.utility import regular_time, regular_df
from abquant.trader.utility import generate_ab_symbol
from abquant.trader.common import Exchange
from abquant.monitor.logger import Logger


class DataLoaderKline(DataLoader):
    def __init__(self, config: Dict):
        super().__init__(config)
        self._logger = Logger("dataloader")
        self.exchange: Exchange = None
        self.symbol = None
        self.trade_type = None
        self.interval = None
        self.start_time = None
        self.end_time = None
        self.data_file = None
        self.data_location = None
        home_dir = os.environ['HOME']
        self.cache_dir = home_dir + '/.abquant/data'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            self._logger.info(f'Data loader cache dir: {self.cache_dir}')
        self.set_config(config)

    """
        config each item from setting dict
    """
    def set_config(self, setting):
        super().set_config(setting)
        try:
            try:
                self.exchange = Exchange(setting.get("exchange"))
            except ValueError:
                raise Exception(f'Dataloader config: exchange incorrect: {setting.get("exchange")}')
            self.symbol = setting.get("symbol")
            self.trade_type = setting.get("trade_type")
            self.interval = setting.get("interval")
            if self.interval is None or self.interval == Interval.MINUTE:
                self.interval = "1m"
            elif self.interval == "1m":
                pass
            else:
                raise Exception(f'Dataloader config: interval incorrect: {self.interval}')
            stime = setting.get("start_time")
            etime = setting.get("end_time")
            self.start_time = regular_time(stime)
            self.end_time = regular_time(etime)
            if stime is not None and self.start_time is None:
                raise Exception(f'Dataloader config: start time misformat: {stime}')
            if etime is not None and self.start_time is None:
                raise Exception(f'Dataloader config: end time misformat: {etime}')
            self.data_file = setting.get("data_file")
            if self.data_file is not None and os.path.isfile(self.data_file):
                self.data_location = DataLocation.LOCAL
            else:
                self.data_location = DataLocation.REMOTE
        except Exception as e:
            self._logger.error(e)

    """
        load csv data, local file or remote aws s3 files
    """
    def load_data(self) -> Dataset:
        assert self.interval == Interval.MINUTE or self.interval == "1m"

        cache_file = ''

        # 检查缓存  todo: 数据合并
        if self.exchange is not None and self.symbol is not None and self.start_time is not None \
                and self.end_time is not None and self.trade_type is not None:
            cache_file = f"{self.exchange.value.lower()}-{self.trade_type.lower()}-{self.symbol.lower()}-1m" \
                       f"-{str(self.start_time)[:19].replace(' ','-')}-{str(self.end_time)[:19].replace(' ','-')}.csv"
            if Path(self.cache_dir + '/' + cache_file).is_file():
                # load from cache
                self._logger.info(f"Load from cache: {self.cache_dir + '/' + cache_file}")
                df_03 = pd.read_csv(self.cache_dir + '/' + cache_file, index_col=0)
                absymbol = generate_ab_symbol(self.symbol, self.exchange)
                dataset: DatasetKline = DatasetKline(self.start_time, self.end_time, absymbol, self.interval)
                dataset.set_data(df_03.to_dict(orient="records"), df_03, df_03.shape[0])
                return dataset

        df_01 = None
        df_02 = None
        if self.data_location == DataLocation.LOCAL:
            # path = Path(self.data_file)
            if self.data_file is not None and os.path.isfile(self.data_file):
                df_01 = pd.read_csv(self.data_file)
                self._logger.debug(df_01.head(1))

        elif self.data_location == DataLocation.REMOTE:
            loader = RemoteLoader(self.exchange, self.symbol, self.trade_type, self.interval,
                                  self.start_time, self.end_time)
            df_01 = loader.load_remote()
            df_02 = df_01
            self._logger.debug(df_01.head(1))

        if df_01 is None:
            self._logger.info('No data loaded, exit')
            return None

        if df_02 is None:
            df_02 = regular_df(df_01, self.exchange, self.symbol, self.interval)

        rn, cn = df_02.shape
        if self.symbol is None:
            self.symbol = df_02.iloc[0]['symbol']
        if self.start_time is None:
            self.start_time = df_02.iloc[0]['datetime']
        if self.end_time is None:
            self.end_time = df_02.iloc[rn - 1]['datetime']

        absymbol = generate_ab_symbol(self.symbol, self.exchange)
        dataset: DatasetKline = DatasetKline(self.start_time, self.end_time, absymbol, self.interval)

        dataset.set_data(df_02.to_dict(orient="records"), df_02, rn)

        # check
        result, msg = dataset.check()
        if not result:
            self._logger.info(f"Error: data check: {msg}, cannot load")
            return None

        # cache
        if cache_file is not None and len(cache_file) > 0:
            df_02.to_csv(self.cache_dir + '/' + cache_file)
        else:
            cache_file = f"{self.exchange.value.lower()}-{self.trade_type.lower()}-{self.symbol.lower()}-1m" \
                         f"-{str(self.start_time)[:19].replace(' ', '-')}-{str(self.end_time)[:19].replace(' ', '-')}.csv"
            df_02.to_csv(self.cache_dir + '/' + cache_file, index=False)

        self._logger.info(f"Loaded k-line bars {rn}")
        return dataset




