
from typing import Dict, Iterable
from datetime import datetime
import os

import pandas as pd
from pandas.core.frame import DataFrame
from pathlib import Path

from abquant.trader.msg import BarData, Interval
from abquant.dataloader.dataloader import DataLoader, Dataset, DataLocation
from abquant.dataloader.datasetkline import DatasetKline
from abquant.dataloader.utility import regular_time


class DataLoaderKline(DataLoader):
    def __init__(self, config: Dict):
        """
        子类须调用该方法初始化
        super().__init__(config)
        """
        super().__init__(config)
        self.exchange = None
        self.symbol = None
        self.trade_type = None
        self.interval = None
        self.start_time = None
        self.end_time = None
        self.data_file = None
        self.data_location = None
        self.set_config(config)
        home_dir = os.environ['HOME']
        self.cache_dir = home_dir + '/.abquant/data'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def set_config(self, setting):
        """
        子类须实现该方法
        """
        super().set_config(setting)
        try:
            self.exchange = setting.get("exchange")
            self.symbol = setting.get("symbol")
            self.trade_type = setting.get("trade_type")
            self.interval = setting.get("interval")
            if self.interval is None or self.interval == Interval.MINUTE or self.interval == "1m":
                self.interval = "1m"
            elif self.interval == "1m":
                pass
            else:
                raise Exception(f'Dataloader config: interval incorrect: {stime}')
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

    def regular_time(self):
        pass

    def load_data(self) -> Dataset:
        """
        1. 子类须实现该方法，
        2. assert, interval是分钟级的
        3. 返回相应规格的DataSet， 该方法会在backtestrunnner中被调用。
        4. 缓存可以考虑在该方法中检测以及建立。

        """
        assert self.interval == Interval.MINUTE or self.interval == "1m"

        dataset: DatasetKline = DatasetKline(self.start_time, self.end_time, self.symbol, self.interval)
        cache_file = ''

        # todo: 检查缓存
        if self.exchange is not None and self.symbol is not None and self.start_time is not None \
                and self.end_time is not None and self.trade_type is not None:
            cache_file = f"{self.exchange.lower()}-{self.trade_type.lower()}-{self.symbol.lower()}-1m" \
                       f"-{str(self.start_time)[:19].replace(' ','-')}-{str(self.end_time)[:19].replace(' ','-')}.csv"
            if Path(self.cache_dir + '/' + cache_file).is_file():
                # load from cache
                pass

        if self.data_location == DataLocation.LOCAL:
            # path = Path(self.data_file)
            if self.data_file is not None and os.path.isfile(self.data_file):
                df_01 = pd.read_csv(self.data_file)
                print(df_01.head(1))
                headers = df_01.columns.values.tolist()
                select_hs, rename_hs = make_columns(headers)
                if len(select_hs) != 7:
                    self.write_log("Error: data headers not correct, cannot load")
                    return None
                df_02 = df_01[select_hs]
                df_02.set_axis(rename_hs, axis='columns', inplace=True)
                # df_02.rename(columns=rename_hs, inplace=True)
                df_02['exchange'] = self.exchange
                df_02['interval'] = self.interval
                df_02['datetime'] = pd.to_datetime(df_02['datetime'], unit='ms')
                print(df_02.head(1))
                print(df_02.shape)

                dataset.bars = df_02.to_dict(orient="records")

                # todo:check
                result, msg = dataset.check()
                if not result:
                    self.write_log(f"Error: data check: {msg}, cannot load")

                # todo:cache
                if cache_file is not None and len(cache_file) > 0:
                    df_02.to_csv(self.cache_dir + '/' + cache_file)
                else:
                    rn, cn = df_02.shape
                    if self.symbol is None:
                        self.symbol = df_02.iloc[0]['symbol']
                    if self.start_time is None:
                        self.start_time = df_02.iloc[0]['datetime']
                    if self.end_time is None:
                        self.end_time = df_02.iloc[rn-1]['datetime']
                    cache_file = f"{self.exchange.lower()}-{self.trade_type.lower()}-{self.symbol.lower()}-1m" \
                        f"-{str(self.start_time)[:19].replace(' ','-')}-{str(self.end_time)[:19].replace(' ','-')}.csv"
                    df_02.to_csv(self.cache_dir + '/' + cache_file)

                return dataset
        elif self.data_location == DataLocation.REMOTE:
            pass
        pass


def make_columns(headers: list) -> (list, list):
    select_hs = []
    rename_hs = []
    if "open_time" in headers:
        select_hs.append('open_time')
        rename_hs.append('datetime')
    if "symbol" in headers:
        select_hs.append('symbol')
        rename_hs.append('symbol')
    if "open" in headers:
        select_hs.append('open')
        rename_hs.append('open_price')
    elif "open_price" in headers:
        select_hs.append('open_price')
        rename_hs.append('open_price')
    elif "o" in headers:
        select_hs.append('o')
        rename_hs.append('open_price')
    if "high" in headers:
        select_hs.append('high')
        rename_hs.append('high_price')
    elif "high_price" in headers:
        select_hs.append('high_price')
        rename_hs.append('high_price')
    elif "h" in headers:
        select_hs.append('h')
        rename_hs.append('high_price')
    if "low" in headers:
        select_hs.append('low')
        rename_hs.append('low_price')
    elif "low_price" in headers:
        select_hs.append('low_price')
        rename_hs.append('low_price')
    elif "l" in headers:
        select_hs.append('l')
        rename_hs.append('low_price')
    if "close" in headers:
        select_hs.append('close')
        rename_hs.append('close_price')
    elif "close_price" in headers:
        select_hs.append('close_price')
        rename_hs.append('close_price')
    elif "c" in headers:
        select_hs.append('c')
        rename_hs.append('close_price')
    if "volume" in headers:
        select_hs.append('volume')
        rename_hs.append('volume')
    elif "v" in headers:
        select_hs.append('v')
        rename_hs.append('volume')
    # if len(select_hs) != 7:
    #     return None, None
    return select_hs, rename_hs


