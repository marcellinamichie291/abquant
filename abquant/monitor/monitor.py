from abc import ABC
from typing import Dict
import json
import time
import random
import logging
from threading import Thread
import asyncio

from .queue import AsyncQueue
from .transmitter import Transmitter

pong_count = 0
MAX_PONG_COUNT = 5
MAX_QUEUE_SIZE = 1000


class Monitor(ABC):

    def __init__(self, setting: dict):
        self.queue = None
        self.wsc = None
        self._consumer_thread = None
        self.setting = setting
        # self.init_monitor(setting)
        # print("Monitor启动")

    # @staticmethod
    def start(self):
        if self.setting is None:
            print("Error: no setting, exit")
            return
        try:
            if self.wsc is None:
                txmt = Transmitter(self.setting)
                self.wsc = txmt.connect_ws()
            if self.queue is None:
                self.init_queue()
                self._consumer_thread = Thread(target=self.run())
                self._consumer_thread.start()
                print("after thread")
                time.sleep(10)
                self.send(json.loads("{\"a\":1, \"b\": \"bb\"}"))
        except Exception as e:
            print("Error: {}", e)

    def stop(self):
        pass
        # self._consumer_thread.setDaemon()

    def init_queue(self, qsize=MAX_QUEUE_SIZE):
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=qsize)

    async def producer(self):
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        for i in range(5):
            await self.queue.put(i)
            await asyncio.sleep(random.randint(0, 2))
            print(f"Put {i}")

    def send(self, data: json):
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        print(f"Send {data}")
        self.queue.put_nowait(data)

    def put1(self, data: json):
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self.queue.put_nowait(data)

    async def consumer(self):
        self.init_queue(MAX_QUEUE_SIZE)
        print("监控：队列初始化完成")
        await self.producer()
        print("监控：示例数据填充完成")
        if self.queue is None:
            print("Error: queue is none.")
            return
        if self.wsc is None:
            print("Error: ws client is none.")
            return
        while True:
            try:
                size = self.queue.qsize()
                print(f'当前队列有：{size} 个元素')
                data = await self.queue.get()
                print(f'拿出元素：{data}')
                self.wsc.send(data)
                size = self.queue.qsize()
                print(f'然后队列有：{size} 个元素')
            except Exception as e:
                print('Error: sleep 1 sec')
                await asyncio.sleep(1)

    def run(self):
        asyncio.run(self.consumer())
        print("async run")
        time.sleep(3)
        print("... run over")

        # loop = asyncio.get_running_loop()
        # ptr = _thread.start_new_thread(asyncio.run(self.run()), ())
        # print(ptr)

    def push_info(self, info: Dict):
        info_json = json.dumps(info)
        self.send(info_json)
