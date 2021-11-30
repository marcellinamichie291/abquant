
import time
import json
from threading import Thread
import requests

import websocket

from .logger import logger

WS_URL = "wss://dct-test001-internal.wecash.net/dct-service-abquant/ws/business?strategy="
MAX_CONNECT_RETRY = 5


class Transmitter:

    client = None
    strategy = None

    def __init__(self, strategy):
        self.strategy = strategy
        self._pp_thread = None  # underlying ping/pong thread

    def connect_ws(self):
        if self.client is not None:
            return self.client
        payload = {}
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        if self.strategy is None:
            logger.debug("Monitor: No strategy config")
            return
        websocket.enableTrace(False)
        try:
            ws = websocket.WebSocketApp(WS_URL + self.strategy, on_message=self.on_message, on_error=self.on_error,
                                        on_close=self.on_close, on_open=self.on_open,
                                        on_ping=self.on_ping, on_pong=self.on_pong)
        except Exception as e:
            logger.debug(e)
            return
        self.client = ws
        # ws.run_forever(ping_interval=30, ping_timeout=5)
        self._pp_thread = Thread(target=self.run_forever, args=(ws,))
        self._pp_thread.start()
        logger.debug("tx: start ping/pong thread")
        time.sleep(1)

        return ws

    def stop(self):
        pass

    def run_forever(self, ws):
        logger.debug("tx: run forever")
        if self.client is None:
            logger.debug("Error: tx: no client to run ping pong thread")
            return
        self.client.run_forever(ping_interval=10, ping_timeout=5)

    def send(self, data):
        if self.client is None:
            # logger.debug("Error: tx: websocket client is none")
            raise Exception("websocket client is none")
        try:
            if isinstance(data, (int, float)):
                data = str(data)
            elif isinstance(data, (list, tuple, set)):
                data = str(data)
            elif isinstance(data, dict):
                data = json.dumps(data)
            else:
                data = str(data)
        except Exception as e:
            logger.debug(f'Data transform error, use str()')
            data = str(data)
        # logger.debug(f"Monitor: send {data}")
        self.client.send(data)

    def on_message(self, ws, msg):
        logger.debug(msg)

    def on_error(self, ws, error):
        logger.error(error)

    def on_open(self, ws):
        self.client = ws
        logger.info("Monitor: WebSocket started")

    def on_close(self, ws, code, msg):
        self.client = None
        if code is not None and code == 1008:   # WS Error Code: Policy Violation, 具体是strategy参数不对
            logger.info("Monitor: No strategy config, WebSocket CLOSED")
            return
        logger.debug(f"WebSocket closed, code: {code}, msg: {msg}")
        i = 1
        time.sleep(3)
        while i <= MAX_CONNECT_RETRY:
            self.client = self.connect_ws()
            time.sleep(i * 2)
            if self.client is not None:
                break
            i += 1
        if self.client is None:
            logger.info(f"Monitor server CLOSED after {i} retry failures")
        else:
            logger.info(f"Monitor server RECONNECT after {i} retries")

    def on_ping(self, pingMsg, ex):
        # ws._send_ping()
        logger.debug("tx: ping")

    def on_pong(self, pongMsg, ex):
        # logger.debug("tx: pong")
        pass


if __name__ == '__main__':
    setting = {
        "strategy": "grid",
        "lark_url": None,
        "log_path": None,
    }
    tx = Transmitter(setting.get("strategy", None))
    client = tx.connect_ws()
    time.sleep(5)
    assert client == tx.client
    client.send("mmmmmmmmmmmmmmmmm")
