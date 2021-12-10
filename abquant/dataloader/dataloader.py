
from abc import ABC, abstractmethod
from typing import Dict, Iterable
from datetime import datetime
from copy import copy
from enum import Enum

from pandas.core.frame import DataFrame

from abquant.trader.msg import BarData, Interval


class Dataset(ABC):
    def __init__(self, start, end, ab_symbol, interval):
        """
        子类须调用该方法初始化
        super().__init__(start, end, ab_symbol, interval)
        """
        self.start: datetime = start
        self.end: datetime = end
        self.ab_symbol: str = ab_symbol
        self.interval: Interval = interval
    
    @abstractmethod
    def __iter__(self) -> Iterable[BarData]:
        """
         返回可迭代对象。
         for bar in dataset:
             do something
         等价于
         data_iter = dataset.__iter__()
         while True:
             try:
                 bar = next(data_iter)
                 do something
             except StopIteration
                 break
        """
        pass

    @abstractmethod
    def __next__(self):
        pass

    @abstractmethod
    def __len__(self) -> int:
        """返回数据集的长度
            len(dataset) 时会调用此方法
        """
        pass

    @abstractmethod
    def copy(self) -> "Dataset":
        """
        generator is not copiable, so copy first before iter may be a good solution.
        在backtestrunnner中的调用方式为:
        dataset_copy = dataset.copy():
        for bar in dataset_copy:
        #  do something
        该设计的原因是， 迭代可能反复进行。然而generator作为迭代器，不能被复制，且只能调用一次，因此dataset类需实现copy方法。该方法最好为浅拷贝。 
         """

        pass

    @abstractmethod
    def check(self) -> bool:
        pass


class DataLoader(ABC):

    _config = None

    def __init__(self, config: Dict):
        """
        子类须调用该方法初始化
        super().__init__(config)
        """
        self.history_data: Dict[str, DataFrame] = {}
        self.set_config(config)
    
    @abstractmethod
    def set_config(self, setting):
        """
        子类须实现该方法
        """
        self._config = setting

    @abstractmethod
    def load_data(self) -> Dataset:
        """
        1. 子类须实现该方法，
        2. assert, interval是分钟级的
        3. 返回相应规格的DataSet， 该方法会在backtestrunnner中被调用。
        4. 缓存可以考虑在该方法中检测以及建立。

        """
        pass
    

class DataLocation(Enum):
    """
    Backtest Data Type.
    """
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


