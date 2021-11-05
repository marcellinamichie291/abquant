from datetime import datetime
import json
import logging
import time
from threading import Thread
from queue import Empty, Queue
from typing import Dict, List, Tuple
from copy import copy
import uuid

from abquant.trader.msg import OrderData, TradeData
from abquant.trader.object import LogData
from abquant.trader.utility import extract_ab_symbol, object_as_dict
from .transmitter import Transmitter
from .util import logger, config_logger

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
        config_logger(self.setting.get("log_path", None))
        try:
            if self.txmt is None:
                self.txmt = Transmitter(self.setting.get("username", None), self.setting.get("password", None))
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

    def default_info(self, run_id: str, event_type: str):
        info = {"event_time": datetime.now().timestamp(),
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "strategy_name": ''.join(run_id.split('-')[:-1]),
                "event_type": event_type,
                "payload": None}
        return info

    def send_order(self, run_id, order: OrderData):
        info = self.default_info(run_id, "order")
        payload = object_as_dict(order)
        info['payload'] = payload
        self.send(info)

    def send_trade(self, run_id, trade: TradeData):
        info = self.default_info(run_id, "order_trade")
        payload = object_as_dict(trade)
        info['payload'] = payload
        self.send(info)

    def send_position(self, run_id, ab_symbol: str, pos: float):
        info = self.default_info(run_id, "position")
        symbol, exchange = extract_ab_symbol(ab_symbol)
        payload = {"symbol": symbol,
                   "exchange": exchange.value,
                   "ab_symbol": ab_symbol,
                   "position": pos}
        info['payload'] = payload
        self.send(info)

    def send_parameter(self, run_id, parameters: Dict):
        info = self.default_info(run_id, "parameter")
        payload = {"type": "parameter",
                   "name": None,
                   "value": None}
        info['payload'] = payload
        for name, value in parameters.items():
            current_info = copy(info)
            current_info['payload']['name'] = name
            current_info['payload']['value'] = value
            self.send(current_info)

    def send_variable(self, run_id, variables: Dict):
        info = self.default_info(run_id, "parameter")
        payload = {"type": "variable",
                   "name": None,
                   "value": None}
        info['payload'] = payload
        for name, value in variables.items():
            current_info = copy(info)
            current_info['payload']['name'] = name
            current_info['payload']['value'] = value
            self.send(current_info)

    def send_log(self, run_id, log: LogData, log_type: str='custom'):
        info = self.default_info(run_id, "log")
        payload = object_as_dict(log)
        payload['level'] = logging.getLevelName(payload['level'])
        payload['type'] = log_type
        info['payload'] = payload
        self.send(info)

    def send_status(self, run_id, status_type: str, ab_symbols: List[str]):
        info = self.default_info(run_id, "status_report")
        payload = {"type": status_type,
                   "message": "",
                   "account_name": self.setting.get("username", None),
                   "ab_symbols": ab_symbols}
        info['payload'] = payload
        self.send(info)

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
                        self.txmt = Transmitter(self.setting.get("username", None), self.setting.get("password", None))
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
