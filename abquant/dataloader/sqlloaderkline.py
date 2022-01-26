from typing import Dict
from datetime import datetime
from abquant.trader.msg import Interval
from abquant.dataloader.dataloader import DataLoader, Dataset
from abquant.dataloader.datasetkline import DatasetKline
from abquant.trader.utility import generate_ab_symbol, extract_ab_symbol
from abquant.trader.common import Exchange
from abquant.monitor.logger import Logger

from clickhouse_driver import Client

DAR_DATA_SQL = """
    SELECT
        symbol, exchange, interval, datetime, open_price, high_price, low_price, close_price, volume, turnover
    FROM
        bar_data
    WHERE 
        symbol = '{}'
        AND exchange = '{}'
        AND type = '{}'
        AND interval = '{}'
        AND datetime >= '{}'
        AND datetime < '{}'
    ORDER BY
        datetime
"""

class SqlLoaderKline(DataLoader):
    default_config = {
        "user": "",
        "password": "",
        "url": "",
        "port": ""
    }
    def __init__(self, config: Dict = None):
        super().__init__(config)
        
        self.client = Client.from_url(f"clickhouse://{config['user']}:{config['password']}@{config['url']}:{config['port']}/abquant?use_numpy=True")

        self._logger = Logger("sqlloader")

    def set_config(self, setting):
        super().set_config(setting)

    """
        sql bar data loader 
    """
    def load_data(self, ab_symbol: str, start: datetime, end: datetime,
                  interval: Interval = Interval.MINUTE) -> Dataset:
        return self._load_data(ab_symbol, start, end, interval=interval)

    def _load_data(self, ab_symbol: str, start: datetime, end: datetime,
                  interval: Interval = Interval.MINUTE) -> Dataset:
        loader = LoaderKline()
        loader.config_loader(ab_symbol, start, end, interval=interval,)

        sql = DAR_DATA_SQL.format(loader.symbol, loader.exchange.value, loader.trade_type, loader.interval.value, loader.start_time, loader.end_time)
        history_df = self.client.query_dataframe(sql)

        rn, cn = history_df.shape
        if loader.exchange is None:
            loader.exchange = Exchange(history_df.iloc[0]['exchange'].upper())
        if loader.symbol is None:
            loader.symbol = history_df.iloc[0]['symbol']
        if loader.start_time is None:
            loader.start_time = datetime.strptime(str(history_df.iloc[0]['datetime']), '%Y-%m-%d %H:%M:%S')
        if loader.end_time is None:
            loader.end_time = datetime.strptime(str(history_df.iloc[rn - 1]['datetime']), '%Y-%m-%d %H:%M:%S')

        absymbol = generate_ab_symbol(loader.symbol, loader.exchange)
        dataset: DatasetKline = DatasetKline(loader.start_time, loader.end_time, absymbol, loader.interval)
        dataset.set_data(history_df.to_dict(orient="records"), history_df, rn)

        return dataset


class LoaderKline:
    def __init__(self):
        self.exchange: Exchange = None
        self.symbol = None
        self.trade_type = None
        self.interval: Interval = None
        self.start_time: datetime = None
        self.end_time: datetime = None

    def config_loader(self, ab_symbol: str, start: datetime, end: datetime,
                      interval: Interval = Interval.MINUTE):

        if ab_symbol is None:
            raise Exception(f'Dataloader: ab_symbol is none')
        symbol, exchange = extract_ab_symbol(ab_symbol)
        if exchange is None:
            raise Exception(f'Dataloader: exchange is none')
        self.exchange = exchange
        self.symbol = symbol
        if self.symbol is None:
            raise Exception(f'Dataloader: symbol is none')
        self.symbol = self.symbol.strip("'\" \n\t")
        if self.exchange == Exchange.BINANCE:
            if self.symbol.islower():
                self.trade_type = 'SPOT'
            elif 'USDT' in self.symbol or 'BUSD' in self.symbol:
                self.trade_type = 'UBC'
            elif 'USD_' in self.symbol:
                self.trade_type = 'BBC'
            else:
                raise Exception(f'Dataloader: ambiguous symbol for sub trading account type')
        if interval != Interval.MINUTE:
            raise Exception(f'Dataloader config: only accept interval MINUTE, but set: {interval}')
        self.interval = interval
        if start is None or end is None:
            raise Exception(f'Dataloader config: neither start nor end time could be empty')
        self.start_time = start
        self.end_time = end


