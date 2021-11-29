
from abc import ABC, abstractmethod
from typing import Dict, Iterable
from datetime import datetime
from copy import copy

from pandas.core.frame import DataFrame

from abquant.trader.msg import BarData, Interval
from abquant.dataloader.dataloader import DataLoader, Dataset


class DatasetKline(Dataset):
    def __init__(self, start, end, ab_symbol, interval):
        """
        子类须调用该方法初始化
        super().__init__(start, end, ab_symbol, interval)
        """
        super().__init__(start, end, ab_symbol, interval)
        self.bars: Dict = {}
        self.cur_pos = -1

    def __iter__(self):
        """
         返回可迭代对象  -> Iterable(BarData)
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
        return self.bars

    def __next__(self) -> BarData:
        self.cur_pos += 1
        if self.cur_pos < self.len:
            return self.list[self.cur_pos]
        else:
            raise StopIteration()

    def __len__(self) -> int:
        """返回数据集的长度
            len(dataset) 时会调用此方法
        """
        return len(self.bars)

    def copy(self) -> "Dataset":
        """
        generator is not copiable, so copy first before iter may be a good solution.
        在backtestrunnner中的调用方式为:
        dataset_copy = dataset.copy():
        for bar in dataset_copy:
        #  do something
        该设计的原因是， 迭代可能反复进行。然而generator作为迭代器，不能被复制，且只能调用一次，因此dataset类需实现copy方法。该方法最好为浅拷贝。 
         """

        return True, ''

    def check(self) -> (bool, str):
        pass


