from abc import ABC
from typing import Dict
import json
import time
import logging

from .queue import AsyncQueue
from .transmitter import Transmitter

pong_count = 0
MAX_PONG_COUNT = 5


class Monitor(ABC):

    def __init__(self, setting: dict):
        self.aqueue = None
        self.wsc = None
        self.init_monitor(setting)
        print("Monitor启动")

    # @staticmethod
    def init_monitor(self, setting: dict):
        if self.aqueue is None:
            aq = AsyncQueue()
            self.aqueue = aq.queue
            aq.start()
            print("after thread")
            time.sleep(10)
            aq.put(json.loads("{\"a\":1, \"b\": \"bb\"}"))
        if self.wsc is None:
            txmt = Transmitter(setting)
            self.wsc = txmt.connect_ws()

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
