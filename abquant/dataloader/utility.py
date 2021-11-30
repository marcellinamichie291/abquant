
from datetime import datetime, timezone
import re


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


if __name__ == '__main__':
    print(regular_time(1619007011))
    print(regular_time(1619007011000))
    print(regular_time(1619007011123456))
    print(regular_time('21-4-21 12 '))
    print(regular_time('2021-4-21'))
    print(regular_time(' 2021-4-21 12:10'))
    print(regular_time('2021-4-21 12:10:11'))
