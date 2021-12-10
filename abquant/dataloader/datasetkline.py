
import random
from pandas.core.frame import DataFrame
from typing import Tuple, Iterable

from abquant.trader.msg import BarData
from abquant.trader.utility import extract_ab_symbol
from abquant.dataloader.dataloader import Dataset
from abquant.monitor.logger import Logger
from abquant.trader.msg import Interval


class DatasetKline(Dataset):
    def __init__(self, start, end, ab_symbol, interval):
        super().__init__(start, end, ab_symbol, interval)
        self._logger = Logger("dataloader")
        self.symbol, self.exchange = extract_ab_symbol(ab_symbol)
        self.dataframe: DataFrame = None
        self.bars: list = []
        self.cur_pos = -1
        self.len = 0

    def __iter__(self) -> Iterable[BarData]:
        """
            如果返回self，next()函数会调用self.__next__()
            如果用现有iter，返回iter(self.bars)，next()会调用假借iter（这里是list）的__next__()，不会调用self.__next__()
        """
        return self

    def __next__(self) -> BarData:
        """
            next()调用，并将取出的item转换为BarData
        """
        self.cur_pos += 1
        if self.cur_pos < self.len:
            bar = self.bars[self.cur_pos]  # todo: return BarData
            bardata = BarData(
                symbol=bar['symbol'],
                exchange=self.exchange,
                interval=self.interval,
                datetime=bar['datetime'],
                gateway_name=None,
                open_price=bar['open_price'],
                high_price=bar['high_price'],
                low_price=bar['low_price'],
                close_price=bar['close_price'],
            )
            return bardata
        else:
            # return None
            raise StopIteration()

    def __len__(self) -> int:
        return self.len

    def set_data(self, data, dataframe: DataFrame, dlen: int = 0):
        if not isinstance(data, list):
            self._logger.error(f'Error: data is not list: {str(data)[:50]}  ...')
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
        newds.len = len(newds.bars)
        return newds

    def check(self) -> Tuple[bool, str]:
        try:
            df_01 = self.dataframe
            if df_01 is None or df_01.empty:
                return False, 'no data'
            # --> 检查列名
            headers = df_01.columns.values.tolist()
            if 'open' not in headers and 'open_price' not in headers and 'o' not in headers:
                return False, 'headers no open price'
            if 'volume' not in headers and 'vol' not in headers and 'v' not in headers:
                return False, 'headers no volume'
            # --> 检查记录条目
            rn, cn = df_01.shape
            if self.interval == Interval.MINUTE or self.interval == '1m':
                minutes = int((self.end - self.start).total_seconds()/60)
                self._logger.info(f'Time interval minutes: {minutes}, real loaded items: {rn}')
            # --> 检查币种
            stat = df_01.groupby('symbol').count()['datetime']
            snum = len(stat)
            if snum != 1:
                self._logger.info(stat)
                return False, 'more than 1 symbol'
            # --> 检查记录日期
            df_02 = df_01.loc[(df_01.datetime < self.start) | (df_01.datetime > self.end)]
            if not df_02.empty:
                self._logger.info(df_02.iloc[0])
                return False, 'datetime out of range'
            # --> 检查数据依赖
            # r1 = random.uniform(0, 1)
            # r2 = random.uniform(0, 1)
            # rmin = int(self.len * min(r1, r2))
            # rmax = int(min(self.len * min(r1, r2) + 100, self.len * max(r1, r2)))
            # gap = 0.0
            # for i in range(rmin, rmax):
            #     df_i = df_01.iloc[i]
            #     df_i1 = df_01.iloc[i+1]
            #     if abs(df_i['close_price'] - df_i1['open_price']) > gap:
            #         gap = abs(df_i['close_price'] - df_i1['open_price'])
            #     # if abs(df_i['close_price'] - df_i1['open_price']) > df_i['close_price'] * 0.001:
            #     #     self._logger.info(df_i)
            #     #     self._logger.info(df_i1)
            #     #     return False, f'kline lack at: {df_i["datetime"]}'
            # self._logger.debug(f'dataloader check: max gap between minutes for {self.ab_symbol}: {gap}')
        except Exception as e:
            return False, 'wrong'
        return True, 'pass'


