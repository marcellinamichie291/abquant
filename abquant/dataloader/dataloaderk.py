
from abc import ABC, abstractmethod
from typing import Dict, Iterable
from datetime import datetime
from copy import copy

from pandas.core.frame import DataFrame

from abquant.trader.msg import BarData, Interval
from abquant.dataloader.dataloader import DataLoader, Dataset


class DataLoaderK(DataLoader):
    def __init__(self, config: Dict):
        """
        子类须调用该方法初始化
        super().__init__(config)
        """
        self.history_data: Dict[str, DataFrame] = {}
        self.set_config(config)
    
    def set_config(setting):
        """
        子类须实现该方法
        """
        pass

    def load_data(self, ab_symbol: str, start: datetime, end: datetime, interval: Interval=Interval.MINUTE) -> Dataset:
        """
        1. 子类须实现该方法，
        2. assert, interval是分钟级的
        3. 返回相应规格的DataSet， 该方法会在backtestrunnner中被调用。
        4. 缓存可以考虑在该方法中检测以及建立。

        """
        pass
    
    


