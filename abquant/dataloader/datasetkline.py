
import random
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
        self.dataframe: DataFrame = None
        self.bars: list = []
        self.cur_pos = -1
        self.len = 0

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
        return iter(self.bars)

    def __next__(self) -> BarData:
        self.cur_pos += 1
        if self.cur_pos < self.len:
            return self.list[self.cur_pos]  # todo: return BarData
        else:
            return None
            # raise StopIteration()

    def __len__(self) -> int:
        """返回数据集的长度
            len(dataset) 时会调用此方法
        """
        return len(self.bars)

    def set_data(self, data, dataframe: DataFrame, dlen: int = 0):
        if not isinstance(data, list):
            print(f'Error: data is not list: {str(data)[:50]}  ...')
            return
        self.bars = data
        self.dataframe = dataframe
        if dlen is None or dlen <= 0:
            self.len = len(self.bars)
        else:
            self.len = dlen

    def copy(self) -> "Dataset":
        newds = DatasetKline(self.start, self.end, self.ab_symbol, self.interval)
        newds.bars = self.bars   # 数据只读情况下，共用一份，节省内存
        newds.dataframe = self.dataframe
        newds.cur_pos = -1
        newds.len = 0
        return newds

    def check(self) -> (bool, str):
        try:
            df_01 = self.dataframe
            # --> 检查列名
            headers = df_01.columns.values.tolist()
            if 'open' not in headers and 'open_price' not in headers and 'o' not in headers:
                return False, 'headers no open price'
            if 'volume' not in headers and 'vol' not in headers and 'v' not in headers:
                return False, 'headers no volume'
            # --> 检查记录条目
            # --> 检查币种
            stat = df_01.groupby('symbol').count()['datetime']
            snum = len(stat)
            if snum != 1:
                print(stat)
                return False, 'more than 1 symbol'
            # --> 检查记录日期
            df_02 = df_01.loc[(df_01.datetime < self.start) | (df_01.datetime > self.end)]
            if not df_02.empty:
                print(df_02.iloc[0])
                return False, 'datetime out of range'
            # --> 检查数据依赖
            r1 = random.uniform(0, 1)
            r2 = random.uniform(0, 1)
            rmin = int(self.len * min(r1, r2))
            rmax = int(min(self.len * min(r1, r2) + 100, self.len * max(r1, r2)))
            gap = 0.0
            for i in range(rmin, rmax):
                df_i = df_01.iloc[i]
                df_i1 = df_01.iloc[i+1]
                if abs(df_i['close_price'] - df_i1['open_price']) > gap:
                    gap = abs(df_i['close_price'] - df_i1['open_price'])
                # if abs(df_i['close_price'] - df_i1['open_price']) > df_i['close_price'] * 0.001:
                #     print(df_i)
                #     print(df_i1)
                #     return False, f'kline lack at: {df_i["datetime"]}'
            print(gap)
        except Exception as e:
            return False, 'wrong'
        return True, 'pass'


