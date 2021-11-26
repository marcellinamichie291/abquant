
from abc import ABC, abstractmethod
from typing import Dict, Iterable
from datetime import datetime
from copy import copy
import os

from pandas.core.frame import DataFrame
import pathlib

from abquant.trader.msg import BarData, Interval
from abquant.dataloader.dataloader import DataLoader, Dataset, DataType


class DataLoaderKline(DataLoader):
    def __init__(self, config: Dict):
        """
        子类须调用该方法初始化
        super().__init__(config)
        """
        super().__init__(config)
        self.exchange = None
        self.symbol = None
        self.interval = None
        self.start_time = None
        self.end_time = None
        self.data_file = None
        self.data_type = None
        self.set_config(config)
        home_dir = os.environ['HOME']
        if not os.path.exists(self.home_dir + '/.abquant/data'):
            os.makedirs(self.home_dir + '/.abquant/data')
        self.cache_dir = home_dir + '/.abquant/data'

    def set_config(self, setting):
        """
        子类须实现该方法
        """
        super().set_config(setting)
        try:
            self.exchange = setting.get("exchange")
            self.symbol = setting.get("symbol")
            self.interval = setting.get("interval")
            self.start_time = datetime.strptime(setting.get("start_time"), '%Y-%m-%d %H:%M:%S')
            self.end_time = datetime.strptime(setting.get("end_time"), '%Y-%m-%d %H:%M:%S')
            self.data_file = setting.get("data_file")
            if self.data_file is not None:
                self.data_type = DataType.LOCAL
            else:
                self.data_type = DataType.REMOTE
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

        # todo: 检查缓存

        if self.data_type == DataType.LOCAL:
            path = pathlib.Path(self.data_file)
            if path.is_absolute() and path.is_file():
                df_01 = DataFrame.read_csv(self.data_file)
        elif self.data_type == DataType.REMOTE:
            pass
        pass
    
    


