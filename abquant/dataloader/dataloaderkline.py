
from abc import ABC, abstractmethod
from typing import Dict, Iterable
from datetime import datetime
from copy import copy

from pandas.core.frame import DataFrame

from abquant.trader.msg import BarData, Interval
from abquant.dataloader.dataloader import DataLoader, Dataset


class DataLoaderKline(DataLoader):
    def __init__(self, config: Dict):
        """
        子类须调用该方法初始化
        super().__init__(config)
        """
        super().__init__(config)
        self.exchange = None
        self.symbol = None
        self.start_time = None
        self.end_time = None

    def set_config(self, setting):
        """
        子类须实现该方法
        """
        super().set_config(setting)
        try:
            self.exchange = setting.get("exchange")
            self.symbol = setting.get("symbol")
            self.start_time = datetime.strptime(setting.get("start_time"), '%Y-%m-%d %H:%M:%S')
            self.end_time = datetime.strptime(setting.get("end_time"), '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(e)

    def regular_time(self):
        pass

    def load_data(self, ab_symbol: str, start: datetime, end: datetime, interval: Interval=Interval.MINUTE) -> Dataset:
        """
        1. 子类须实现该方法，
        2. assert, interval是分钟级的
        3. 返回相应规格的DataSet， 该方法会在backtestrunnner中被调用。
        4. 缓存可以考虑在该方法中检测以及建立。

        """
        assert interval == Interval.MINUTE

        pass
    
    


