from datetime import datetime
import time
import hashlib
import hmac
from pytz import timezone


def generate_timestamp(expire_after: float = 30) -> int:
    """生成时间戳"""
    return int(time.time() * 1000 + expire_after * 1000)


def sign(secret: bytes, data: bytes) -> str:
    """生成签名"""
    return hmac.new(
        secret, data, digestmod=hashlib.sha256
    ).hexdigest()

def generate_datetime(timestamp: str) -> datetime:
    """生成时间"""
    if "." in timestamp:
        part1, part2 = timestamp.split(".")
        if len(part2) > 7:
            part2 = part2[:6] + "Z"
            timestamp = ".".join([part1, part2])

        dt: datetime = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        dt: datetime = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")

    return dt


def generate_datetime_2(timestamp: int) -> datetime:
    """生成时间"""
    dt: datetime = datetime.fromtimestamp(timestamp)
    return dt


def get_float_value(data: dict, key: str) -> float:
    """获取字典中对应键的浮点数值"""
    data_str: str = data.get(key, "")
    if not data_str:
        return 0.0
    return float(data_str)


def get_float_value(data: dict, key: str) -> float:
    """获取字典中对应键的浮点数值"""
    data_str: str = data.get(key, "")
    if not data_str:
        return 0.0
    return float(data_str)
