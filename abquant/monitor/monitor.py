from typing import Dict
import json
import time
from threading import Thread
from queue import Empty, Queue

from .transmitter import Transmitter

pong_count = 0
MAX_PONG_COUNT = 5
MAX_QUEUE_SIZE = 1000
MAX_BUFFER_SIZE = 1000


class Monitor(Thread):
    queue = None
    txmt: Transmitter = None
    setting = None
    buffer = None

    def __init__(self, setting: dict):
        Thread.__init__(self)
        self.setting = setting
        self.buffer = []
        self.queue: Queue = Queue(maxsize=MAX_QUEUE_SIZE)

    def run(self):
        if self.setting is None:
            print("Error: no setting, exit")
            return
        try:
            if self.txmt is None:
                self.txmt = Transmitter(self.setting)
                self.txmt.connect_ws()
                time.sleep(1)
                self.txmt.client.send("ttttttttttttttttt")
            print("qu: self run consumer")
            # asyncio.run(self.consumer())
            self.consumer()
        except Exception as e:
            print("Error: {}", e)

    def send(self, data: json):
        if self.queue.full():
            print("Error: qu: queue is full")
            return
        self.queue.put_nowait(data)
        print(f"qu: send: put to queue: {data}  {self.queue.qsize()}\n")

    def consumer(self):
        self.queue.put(1.5)
        self.queue.put('2')
        self.queue.put("{\"c\":3}")
        self.queue.put([1, '2'])
        self.queue.put({1, '2'})
        self.queue.put((1, 2))
        print("监控：示例数据填充完成")
        if self.queue is None:
            print("Error: qu: queue is none.")
            return
        if self.txmt is None or self.txmt.client is None:
            print("Error: tx: ws client is none.")
            return
        cycles = 0
        while True:
            try:
                self.send_buffer()
                size = self.queue.qsize()
                print(f'qu: 当前队列有：{size} 个元素')
                data = self.queue.get(timeout=1)
                print(f'qu: 拿出元素：{data}, 发送...')
                # await self.txmt.client.send(str(data))
                try:
                    self.txmt.send(data)
                except Exception as e:
                    print(f'Error: tx: ws发送错误：{e}')
                    self.push_buffer(data)
                    cycles += 1
                    if cycles > 10:
                        self.txmt = Transmitter(self.setting)
                        self.txmt.connect_ws()
                        time.sleep(1)
                        self.txmt.client.send("rrrrrrrrrrrrrrr")
                    continue
                size = self.queue.qsize()
                print(f'qu: 然后队列有：{size} 个元素')
            except Empty:
                # print('empty queue')
                continue
            except Exception as e:
                print('Error: qu: ', e)
                continue

    def push_buffer(self, data) -> int:
        if len(self.buffer) < MAX_BUFFER_SIZE:
            self.buffer.append(data)
            return len(self.buffer)
        else:
            print("Error: qu: buffer is full")
            return -1

    def send_buffer(self):
        blen = len(self.buffer)
        print(f'qu: buffer size {blen}')
        if len(self.buffer) > 0:
            for buf in self.buffer:
                try:
                    self.txmt.send(buf)
                except Exception as e:
                    print(f'Error: tx: ws发送错误：{e}')
                    return -2
                print(f"as: send buffer: {buf}")
            self.buffer.clear()
            print(f'qu: buffer clear {blen}')
            return blen
        return 0
