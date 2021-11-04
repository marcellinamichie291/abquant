import json
import time
from threading import Thread
from queue import Empty, Queue

from .transmitter import Transmitter
from .util import logger

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
        logger.info("监控：队列初始化（{}）".format(MAX_QUEUE_SIZE))

    def run(self):
        if self.setting is None:
            logger.error("Error: no setting, exit")
            return
        try:
            if self.txmt is None:
                self.txmt = Transmitter(self.setting)
                self.txmt.connect_ws()
                time.sleep(1)
                self.txmt.client.send("test: websocket start")
            # asyncio.run(self.consumer())
            self.consumer()
        except Exception as e:
            logger.debug(f"Error: {e}")

    def send(self, data: json):
        # if self.txmt is None or self.txmt.client is None:
        #     logger.error("Error: websocket client is None.")
        #     return
        if self.queue.full():
            logger.error("Error: qu: queue is full")
            return
        self.queue.put_nowait(data)
        logger.debug(f"监控: 放入队列: {data}, 目前长度: {self.queue.qsize()}")

    def consumer(self):
        # self.queue.put(1.5)
        # self.queue.put('2')
        # self.queue.put("{\"c\":3}")
        # self.queue.put([1, '2'])
        # self.queue.put({1, '2'})
        # self.queue.put((1, 2))
        # logger.debug("监控：示例数据填充完成")
        if self.queue is None:
            logger.error("Error: qu: queue is none.")
            return
        if self.txmt is None or self.txmt.client is None:
            logger.error("Error: tx: ws client is none.")
            return
        logger.info("监控：启动完成")
        cycles = 0
        while True:
            try:
                self.send_buffer()
                size = self.queue.qsize()
                # logger.debug(f'qu: 当前队列有：{size} 个元素')
                data = self.queue.get(timeout=1)
                logger.debug(f'监控: 拿出元素：{data}, 发送...')
                # await self.txmt.client.send(str(data))
                try:
                    self.txmt.send(data)
                except Exception as e:
                    logger.error(f'Error: tx: ws发送错误：{e}')
                    self.push_buffer(data)
                    cycles += 1
                    if cycles > 10:
                        self.txmt = Transmitter(self.setting)
                        self.txmt.connect_ws()
                        time.sleep(1)
                        self.txmt.client.send("test: websocket restart")
                    continue
                size = self.queue.qsize()
                logger.debug(f'监控: 当前队列长度：{size}')
            except Empty:
                # logger.debug('empty queue')
                continue
            except Exception as e:
                logger.error(f'Error: qu: {e}')
                continue

    def push_buffer(self, data) -> int:
        if len(self.buffer) < MAX_BUFFER_SIZE:
            self.buffer.append(data)
            return len(self.buffer)
        else:
            logger.debug("Error: qu: buffer is full")
            return -1

    def send_buffer(self):
        blen = len(self.buffer)
        # logger.debug(f'qu: buffer size {blen}')
        if len(self.buffer) > 0:
            for buf in self.buffer:
                try:
                    self.txmt.send(buf)
                except Exception as e:
                    logger.error(f'Error: tx: ws发送错误：{e}')
                    raise
                logger.debug(f"as: send buffer: {buf}")
            self.buffer.clear()
            logger.debug(f'qu: buffer clear {blen}')
            return blen
        return 0
