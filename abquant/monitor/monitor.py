from abc import ABC
from typing import Dict
import json
import time
import random
import logging
from threading import Thread
import asyncio
from queue import Empty, Queue

# from .queue import AsyncQueue
from .transmitter import Transmitter

pong_count = 0
MAX_PONG_COUNT = 5
MAX_QUEUE_SIZE = 1000


class Monitor(Thread):
    queue = None
    txmt: Transmitter = None
    # _consumer_thread = None
    setting = None
    buffer = None

    def __init__(self, setting: dict):
        Thread.__init__(self)
        self.setting = setting
        self.buffer = []
        self.queue: Queue = Queue(maxsize=MAX_QUEUE_SIZE)
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
            print("qu: self run consumer")
            # asyncio.run(self.consumer())
            self.consumer()
            # ------ 后面的不执行 ------
            # time.sleep(3)
            # print("... run over")
            # self.run1()
            print("qu: after asyncio run")
            time.sleep(10)
            self.send(json.loads("{\"a\":1, \"b\": \"bb\"}"))
            # else:
            #     print(f'What? queue exist: {self.queue}')
        except Exception as e:
            print("Error: {}", e)

    # def stop(self):
    #     pass
    #     # self._consumer_thread.setDaemon()

    # def init_queue(self, qsize=MAX_QUEUE_SIZE):
    #     if self.queue is None:
    #         self.queue = asyncio.Queue(maxsize=qsize)

    # async def producer(self):
    #     if self.queue is None:
    #         self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    #     for i in range(3):
    #         await self.queue.put(i)
    #         await asyncio.sleep(random.randint(0, 2))
    #         print(f"Put {i}")

    def send(self, data: json):
        # if self.queue is None:
        #     # self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        #     if len(self.buffer) < MAX_BUFFER_SIZE:
        #         self.buffer.append(data)
        #         return
        #     else:
        #         print("Error: qu: async buffer is full")
        #         return
        # if len(self.buffer) > 0:
        #     for buf in self.buffer:
        #         if self.queue.qsize() >= MAX_QUEUE_SIZE - 1:
        #             print("Error: qu: async queue is full")
        #             return
        #         else:
        #             self.queue.put_nowait(buf)
        #             print(f"qu: send: buffer to queue: {data}  {self.queue.qsize()}")
        #     self.buffer.clear()
        if self.queue.full():
            print("Error: qu: queue is full")
            return
        self.queue.put_nowait(data)
        print(f"qu: send: put to queue: {data}  {self.queue.qsize()}")

    def consumer(self):
        # self.init_queue(MAX_QUEUE_SIZE)
        # print("监控：队列初始化完成")
        # await self.producer()
        self.queue.put(1)
        self.queue.put('2')
        self.queue.put("{\"c\":3}")
        print("监控：示例数据填充完成")
        if self.queue is None:
            print("Error: qu: queue is none.")
            return
        if self.txmt is None or self.txmt.client is None:
            print("Error: tx: ws client is none.")
            return
        while True:
            try:
                size = self.queue.qsize()
                print(f'qu: 当前队列有：{size} 个元素')
                # data = await self.queue.get()
                data = self.queue.get(timeout=1)
                print(f'qu: 拿出元素：{data}, 发送...')
                # await self.txmt.client.send(str(data))
                self.txmt.client.send(str(data))
                size = self.queue.qsize()
                print(f'qu: 然后队列有：{size} 个元素')
            except Empty:
                print('empty queue')
                continue
            except Exception as e:
                print('Error: qu: ', e)
                continue
                # await asyncio.sleep(1)

    # def run1(self):
    #     print("qu: async run")
    #     asyncio.run(self.consumer())
    #     time.sleep(3)
    #     print("qu: ... run over")
    #
    #     # loop = asyncio.get_running_loop()
    #     # ptr = _thread.start_new_thread(asyncio.run(self.run()), ())
    #     # print(ptr)

    def push_info(self, info: Dict):
        info_json = json.dumps(info)
        self.send(info_json)
