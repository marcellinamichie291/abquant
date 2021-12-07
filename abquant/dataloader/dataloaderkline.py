
from typing import Dict, Iterable
from datetime import datetime
import os

import pandas as pd
from pandas.core.frame import DataFrame
from pathlib import Path

from abquant.trader.msg import Interval
from abquant.dataloader.dataloader import DataLoader, Dataset, DataLocation
from abquant.dataloader.datasetkline import DatasetKline
from abquant.dataloader.utility import regular_time, make_columns
from abquant.trader.utility import generate_ab_symbol
from abquant.trader.common import Exchange


class DataLoaderKline(DataLoader):
    def __init__(self, config: Dict):
        super().__init__(config)
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
            if self.interval is None or self.interval == Interval.MINUTE or self.interval == "1m":
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
            print(e)

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
                print(f"Load from cache: {self.cache_dir + '/' + cache_file}")
                df_03 = pd.read_csv(self.cache_dir + '/' + cache_file, index_col=0)
                absymbol = generate_ab_symbol(self.symbol, self.exchange)
                dataset: DatasetKline = DatasetKline(self.start_time, self.end_time, absymbol, self.interval)
                dataset.set_data(df_03.to_dict(orient="records"), df_03, df_03.shape[0])
                return dataset

        df_01 = None
        if self.data_location == DataLocation.LOCAL:
            # path = Path(self.data_file)
            if self.data_file is not None and os.path.isfile(self.data_file):
                df_01 = pd.read_csv(self.data_file)
                print(df_01.head(1))

        elif self.data_location == DataLocation.REMOTE:
            pass

        if df_01 is None:
            print('No data loaded, exit')
            return None

        headers = df_01.columns.values.tolist()
        select_hs, rename_hs = make_columns(headers)
        if select_hs is not None and len(select_hs) != 7:
            print("Error: data headers not correct, cannot load")
            return None
        df_02 = df_01[select_hs]
        df_02.set_axis(rename_hs, axis='columns', inplace=True)
        # df_02.rename(columns=rename_hs, inplace=True)
        df_02.sort_values(by=['datetime'], ascending=True, inplace=True)
        df_02['exchange'] = self.exchange.value
        df_02['interval'] = self.interval
        df_02['datetime'] = pd.to_datetime(df_02['datetime'], unit='ms')
        print(df_02.head(1))
        print(df_02.shape)

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
            print(f"Error: data check: {msg}, cannot load")
            return None

        # cache
        if cache_file is not None and len(cache_file) > 0:
            df_02.to_csv(self.cache_dir + '/' + cache_file)
        else:
            cache_file = f"{self.exchange.value.lower()}-{self.trade_type.lower()}-{self.symbol.lower()}-1m" \
                         f"-{str(self.start_time)[:19].replace(' ', '-')}-{str(self.end_time)[:19].replace(' ', '-')}.csv"
            df_02.to_csv(self.cache_dir + '/' + cache_file, index=False)

        print(f"Loaded k-line bars {rn}")
        return dataset




