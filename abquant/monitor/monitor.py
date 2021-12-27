from datetime import datetime
import json
import logging
import time
from threading import Thread
from queue import Empty, Queue
from typing import Dict, List
from copy import copy, deepcopy
import uuid

from abquant.trader.msg import OrderData, TradeData
from abquant.trader.object import LogData
from abquant.trader.utility import extract_ab_symbol, object_as_dict
from .notify_lark import notify_lark, LarkMessage, TypeEnum
from .transmitter import Transmitter
from .logger import Logger

MAX_QUEUE_SIZE = 10000
MAX_BUFFER_SIZE = 100000
USE_WS_TRANSMITTER = False


class Monitor(Thread):
    queue = None
    txmt: Transmitter = None
    setting = None
    strategy = None
    buffer = None
    lark_url = None
    _logger = None

    def __init__(self, setting: dict):
        Thread.__init__(self)
        self._logger = Logger("monitor")
        self.setting = setting
        self.strategy = setting.get("strategy", None)
        if self.strategy is None:
            self._logger.info("Monitor: No strategy config, cannot upload log")
        self.lark_url = setting.get("lark_url", None)
        if self.lark_url is None:
            self._logger.info("Monitor: No lark url config, cannot send lark")
        self.log_path = setting.get("log_path", None)
        if self.log_path is None:
            self._logger.info("Monitor: No log path config, default to ./logs/")
        self.buffer = []
        self.queue: Queue = Queue(maxsize=MAX_QUEUE_SIZE)
        self._logger.debug("Monitor: queue length {}".format(MAX_QUEUE_SIZE))
        self._logger.info("Monitor initiated")

    def run(self):
        try:
            if self.txmt is None and USE_WS_TRANSMITTER:
                self.txmt = Transmitter(self.strategy)
                self.txmt.connect_ws()
                time.sleep(1)
        except Exception as e:
            self._logger.debug(f"Error: {e}")
        try:
            self.consumer()
        except Exception as e:
            self._logger.debug(f"Error: {e}")

    def send(self, data: json):
        if self.queue.full():
            self._logger.debug("Monitor: queue is full")
            return
        self.queue.put_nowait(data)

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
            current_info = deepcopy(info)
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
            current_info = deepcopy(info)
            current_info['payload']['name'] = name
            current_info['payload']['value'] = value
            self.send(current_info)

    def send_log(self, run_id, log: LogData, log_type: str = 'custom'):
        info = self.default_info(run_id, "log")
        info['gateway_name'] = log.gateway_name
        payload = object_as_dict(log)
        payload['level'] = logging.getLevelName(payload['level'])
        payload['type'] = log_type
        info['payload'] = payload
        self.send(info)

    def send_status(self, run_id, status_type: str, ab_symbols: List[str]):
        info = self.default_info(run_id, "status_report")
        payload = {"type": status_type,
                   "message": "",
                   "ab_symbols": ab_symbols}
        info['payload'] = payload
        self.send(info)

    def send_notify_lark(self, run_id, msg: str, title: str = '', content: list = None):
        if self.lark_url is None:
            return
        info = self.default_info(run_id, "lark")
        payload = {"lark_group_robot_url": self.lark_url,
                   "message": msg}
        info['payload'] = payload
        self.send(info)
        if content is None or type(content) is not list or type(content[0]) is not list:
            notify_lark.put(LarkMessage(self.strategy, self.lark_url, TypeEnum.TEXT, text=msg))
        else:
            notify_lark.put(LarkMessage(self.strategy, self.lark_url, TypeEnum.POST, title=title, content=content))

    def consumer(self):
        if self.queue is None:
            self._logger.debug("Error: qu: queue is none.")
            return
        self._logger.info("Monitor Started")
        cycles = 1
        while True:
            try:
                if USE_WS_TRANSMITTER:
                    self.send_buffer()
            except Exception as e:
                self._logger.debug(f'Error: buffer: {e}')

            try:
                data = self.queue.get(timeout=1)
                self._logger.debug(f'Monitor: take element to send: {data}')
                self._logger.print_log_format(data)
                try:
                    if USE_WS_TRANSMITTER:
                        self.txmt.send(data)
                except Exception as e:
                    self._logger.debug(f'Error: Queue send: {e},  put into buffer')
                    self.push_buffer(data)
                    # time.sleep(1)
                    cycles += 1
                    if cycles > 10:
                        self.txmt = Transmitter(self.strategy)
                        self.txmt.connect_ws()
                        time.sleep(2)
                        if self.txmt is not None and self.txmt.client is not None:
                            self.txmt.client.send("test: websocket restart")
                        cycles = 1
                    continue
                size = self.queue.qsize()
                self._logger.debug(f'Monitor: current queue length {size}')
            except Empty:
                continue
            except Exception as e:
                self._logger.debug(f'Error: qu: {e}')
                continue

    def push_buffer(self, data) -> int:
        if len(self.buffer) < MAX_BUFFER_SIZE:
            self.buffer.append(data)
            return len(self.buffer)
        else:
            self._logger.debug("Error: Buffer is full")
            return -1

    def send_buffer(self):
        blen = len(self.buffer)
        self._logger.debug(f'qu: buffer size {blen}')
        if self.txmt is None or self.txmt.client is None:
            self._logger.debug("Error: buffer: ws client is none.")
            return
        if len(self.buffer) > 0:
            for buf in self.buffer:
                try:
                    self.txmt.send(buf)
                except Exception as e:
                    self._logger.debug(f'Error: Buffer send: {e}')
                    raise
                self._logger.debug(f"qu: send buffer: {buf}")
            self.buffer.clear()
            self._logger.info(f'Resend {blen} elements while disconnection')
            return blen
        return 0
