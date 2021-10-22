from abc import ABC
import asyncio
import websocket
import time
import threading
import random
import json

MAX_QUEUE_SIZE = 1000


class AsyncQueue:

    queue = None

    def __init__(self):
        # threading.Thread.__init__(self)
        # self.threadID = time.time()
        self.name = "asyncqueue"
        self.counter = 0
        # if self.queue is None:
        #     self.queue = asyncio.Queue(maxsize=qsize)

    def init_queue(self, qsize=1000):
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=qsize)

    async def producer(self):
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        for i in range(10):
            await self.queue.put(i)
            await asyncio.sleep(random.randint(0, 2))
            print(f"Put {i}")

    def put(self, data: json):
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self.queue.put_nowait(data)

    async def consumer(self, wsc):
        self.init_queue(1000)
        print("监控：队列初始化完成")
        await self.producer()
        print("监控：示例数据填充完成")
        if self.queue is None:
            print("Error: queue is none.")
        while True:
            try:
                size = self.queue.qsize()
                print(f'当前队列有：{size} 个元素')
                data = await self.queue.get()
                print(f'拿出元素：{data}')
                size = self.queue.qsize()
                print(f'然后队列有：{size} 个元素')
            except Exception as e:
                print('Error: sleep 1 sec')
                await asyncio.sleep(1)

    async def run1(self):
        print("监控：异步队列开始运行")
        now = lambda: time.time()
        start = now()
        loop = asyncio.get_event_loop()
        asyncio.create_task(self.producer())
        task = loop.create_task(self.consumer())
        print(task)
        # loop.run_until_complete(task)
        # print(task)
        print('TIME: ', now() - start)

        # asyncio.create_task(self.producer())
        # con = asyncio.create_task(self.consumer())
        # await con

    def run(self, wsc):
        asyncio.run(self.consumer())
        print("async run")
        time.sleep(3)
        print("... run over")

        # loop = asyncio.get_running_loop()
        # ptr = _thread.start_new_thread(asyncio.run(self.run()), ())
        # print(ptr)


