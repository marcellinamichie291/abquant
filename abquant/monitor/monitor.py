from abc import ABC
from typing import Dict
import json
import time

pong_count = 0
MAX_PONG_COUNT = 5


class Monitor(ABC):

    def __init__(self, setting: dict):
        pass

    def login(self, setting: Dict):
        pass

    def send(self, info: str):
        pass
