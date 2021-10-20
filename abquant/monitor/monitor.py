from abc import ABC
from typing import Dict
import json
import logging

from .aqueue import AsyncQueue
from .transmitter import Transmitter

pong_count = 0
MAX_PONG_COUNT = 5


class Monitor(ABC):
    aqueue = None
    wsc = None

    def __init__(self):
        Monitor.init_monitor()

    @staticmethod
    def init_monitor(self):
        if self.aqueue is None:
            aq = AsyncQueue()
            aqueue = aq.queue
        if self.wsc is None:
            txmt = Transmitter()
            self.wsc = txmt.init_ws()

    def login(self, setting: Dict):
        pass

    def send(self, info: str):
        pass

    def send(self, info: json):

        pass

    def send2(self, info: str):
        pass

    def push_info(self, info: Dict):
        info_json = json.dumps(info)
        self.send(info_json)
