
from datetime import datetime, timezone
import re
from pandas.core.frame import DataFrame
import pandas as pd
from typing import Tuple, List


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False


def regular_time(untime) -> datetime:
    if untime is None:
        return None
    suntime = str(untime).strip()
    if is_number(suntime) and untime >= 1E9 and untime <= 1E16:  # after year 2001
        untime = round(untime)
        suntime = str(untime).strip()
        div = 10 ** (len(suntime) - 10)
        untime = round(untime / div)    # degrade to second
        return datetime.fromtimestamp(untime, timezone.utc)
    else:
        # dtex = r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2} \d{1,2}(:\d{1,2}){0,2})'
        # match_res = re.search(dtex, suntime)
        if re.search(r'(\d{2,4}[-]\d{1,2}[-]\d{1,2})', suntime) is not None:
            hyphen = '-'
        elif re.search(r'(\d{2,4}[/]\d{1,2}[/]\d{1,2})', suntime) is not None:
            hyphen = '/'
        else:
            print(f'Unrecognized hyphen in datetime: {suntime}')
            return None
        # if statement should be in order
        if re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', suntime) is not None:
            year = 'Y'
        elif re.search(r'(\d{2}[-/]\d{1,2}[-/]\d{1,2})', suntime) is not None:
            year = 'y'
        else:
            print(f'Unrecognized year in datetime: {suntime}')
            return None
        # if statement should be in order
        if re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2} \d{1,2}(:\d{1,2}){2})', suntime) is not None:
            format = f'%{year}{hyphen}%m{hyphen}%d %H:%M:%S'
        elif re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2} \d{1,2}:\d{1,2})', suntime) is not None:
            format = f'%{year}{hyphen}%m{hyphen}%d %H:%M'
        elif re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2} \d{1,2})', suntime) is not None:
            format = f'%{year}{hyphen}%m{hyphen}%d %H'
        elif re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})', suntime) is not None:
            format = f'%{year}{hyphen}%m{hyphen}%d'
        else:
            print(f'Unrecognized time in datetime: {suntime}')
            return None
        try:
            dt = datetime.strptime(suntime, format)
            return dt
        except Exception as ex:
            print(f'Unrecognized datetime: {suntime}')
            return None


def make_columns(headers: list) -> Tuple[List, List]:
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


def regular_df(df_01: DataFrame, exchange: str, symbol: str, interval: str) -> DataFrame:
    if df_01 is None or not isinstance(df_01, DataFrame):
        return df_01
    if df_01.shape[0] == 0:
        return df_01
    headers = df_01.columns.values.tolist()
    select_hs, rename_hs = make_columns(headers)
    if select_hs is not None:
        if len(select_hs) == 6 and 'symbol' not in select_hs:
            df_01.loc[:, 'symbol'] = symbol
            select_hs.append('symbol')
            rename_hs.append('symbol')
        if len(select_hs) != 7:
            print("Error: data headers not correct, cannot load")
            return None
    df_02 = df_01[select_hs]
    df_02.set_axis(rename_hs, axis='columns', inplace=True)
    # df_02.rename(columns=rename_hs, inplace=True)
    df_02.sort_values(by=['datetime'], ascending=True, inplace=True)
    df_02.loc[:, 'exchange'] = exchange
    df_02.loc[:, 'interval'] = interval
    df_02.loc[:, 'datetime'] = pd.to_datetime(df_02['datetime'], unit='ms')
    print(df_02.head(1))
    print(df_02.shape)
    return df_02


if __name__ == '__main__':
    print(regular_time(1619007011))
    print(regular_time(1619007011000))
    print(regular_time(1619007011123456))
    print(regular_time(1619007011.123456))
    print(regular_time('21-4-21 12 '))
    print(regular_time('2021-4-21'))
    print(regular_time(' 2021-4-21 12:10'))
    print(regular_time('2021-4-21 12:10:11'))
