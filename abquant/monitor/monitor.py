from abc import ABC
from typing import Dict
import json
import time
import random
import logging
from threading import Thread
import asyncio

# from .queue import AsyncQueue
from .transmitter import Transmitter

pong_count = 0
MAX_PONG_COUNT = 5
MAX_QUEUE_SIZE = 1000
MAX_BUFFER_SIZE = 1000


class Monitor(Thread):
    queue = None
    txmt: Transmitter = None
    _consumer_thread = None
    setting = None
    buffer = None

    def __init__(self, setting: dict):
        Thread.__init__(self)
        self.setting = setting
        self.buffer = []
        # self.init_monitor(setting)

    # @staticmethod
    def run(self):
        if self.setting is None:
            print("Error: no setting, exit")
            return
        try:
            if self.txmt is None:
                self.txmt = Transmitter(self.setting)
                self.txmt.connect_ws()
                time.sleep(10)
                self.txmt.client.send("ttttttttttttttttt")
            # if self.queue is None:
            # self.init_queue()
            # self._consumer_thread = Thread(target=self.run1())
            # self._consumer_thread = Thread(target=asyncio.run(self.consumer()))
            # self._consumer_thread.start()
            print("as: self run consumer")
            asyncio.run(self.consumer())
            # time.sleep(3)
            # print("... run over")
            # self.run1()
            print("as: after asyncio run")
            time.sleep(10)
            self.send(json.loads("{\"a\":1, \"b\": \"bb\"}"))
            # else:
            #     print(f'What? queue exist: {self.queue}')
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
        for i in range(3):
            await self.queue.put(i)
            await asyncio.sleep(random.randint(0, 2))
            print(f"Put {i}")

    def send(self, data: json):
        if self.queue is None:
            # self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
            if len(self.buffer) < MAX_BUFFER_SIZE:
                self.buffer.append(data)
                return
            else:
                print("Error: as: async buffer is full")
                return
        if len(self.buffer) > 0:
            for buf in self.buffer:
                if self.queue.qsize() >= MAX_QUEUE_SIZE - 1:
                    print("Error: as: async queue is full")
                    return
                else:
                    self.queue.put_nowait(buf)
                    print(f"as: send: buffer to queue: {data}  {self.queue.qsize()}")
            self.buffer.clear()
        if self.queue.qsize() >= MAX_QUEUE_SIZE - 1:
            print("Error: as: async queue is full")
            return
        self.queue.put_nowait(data)
        print(f"as: send: put to queue: {data}  {self.queue.qsize()}")

    async def consumer(self):
        self.init_queue(MAX_QUEUE_SIZE)
        print("监控：队列初始化完成")
        await self.producer()
        print("监控：示例数据填充完成")
        if self.queue is None:
            print("Error: as: queue is none.")
            return
        if self.txmt is None or self.txmt.client is None:
            print("Error: tx: ws client is none.")
            return
        while True:
            try:
                size = self.queue.qsize()
                print(f'as: 当前队列有：{size} 个元素')
                data = await self.queue.get()
                print(f'as: 拿出元素：{data}')
                # await self.txmt.client.send(str(data))
                self.txmt.client.send(str(data))
                size = self.queue.qsize()
                print(f'as: 然后队列有：{size} 个元素')
            except Exception as e:
                print('Error: as: ', e)
                await asyncio.sleep(1)

    def run1(self):
        print("as: async run")
        asyncio.run(self.consumer())
        time.sleep(3)
        print("as: ... run over")

        # loop = asyncio.get_running_loop()
        # ptr = _thread.start_new_thread(asyncio.run(self.run()), ())
        # print(ptr)

    def push_info(self, info: Dict):
        info_json = json.dumps(info)
        self.send(info_json)
