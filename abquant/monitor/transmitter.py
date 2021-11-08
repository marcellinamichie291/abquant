
import time
import json
from threading import Thread
import requests

import websocket

from .util import logger

LOGIN_URL = "https://dct-test001.wecash.net/dct-business-api/login"
WS_URL = "wss://dct-test001-internal.wecash.net/dct-service-abquant/ws/business?access_token="
MAX_CONNECT_RETRY = 5


class Transmitter:

    client = None
    username = None
    password = None

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._pp_thread = None  # underlying ping/pong thread

    def connect_ws(self):
        if self.client is not None:
            return self.client
        payload = {}
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        if self.username is None or self.password is None:
            logger.debug("监控：初始化：用户名或密码不存在")
            return
        login_url = LOGIN_URL + "userName=" + self.username + "&password=" + self.password
        access_token = None
        try:
            response = requests.request("GET", login_url, headers=headers, data=payload)
            jn = json.loads(response.text)
            access_token = jn.get("data").get("access_token")
            # logger.debug(access_token)
        except Exception:
            return

        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(WS_URL + access_token, on_message=self.on_message, on_error=self.on_error,
                                    on_close=self.on_close, on_open=self.on_open,
                                    on_ping=self.on_ping, on_pong=self.on_pong)
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
        if isinstance(data, (int, float)):
            data = str(data)
        elif isinstance(data, (list, tuple, set)):
            data = str(data)
        elif isinstance(data, dict):
            data = json.dumps(data)
        else:
            pass
        # logger.debug(f"监控：发送：{data}")
        self.client.send(data)

    def on_message(self, ws, msg):
        logger.debug(msg)

    def on_error(self, ws, error):
        logger.error(error)

    def on_open(self, ws):
        self.client = ws
        logger.info("监控：WebSocket开启")

    def on_close(self, ws, code, msg):
        logger.info(f"tx: close, code: {code}, msg: {msg}")
        self.client = None
        i = 1
        time.sleep(3)
        while i <= MAX_CONNECT_RETRY:
            self.client = self.connect_ws()
            time.sleep(i * 2)
            if self.client is not None:
                break
            i += 1
        logger.info(f"tx: Reconnect after {i} retries")

    def on_ping(self, pingMsg, ex):
        # ws._send_ping()
        logger.debug("tx: ping")

    def on_pong(self, pongMsg, ex):
        # logger.debug("tx: pong")
        pass


if __name__ == '__main__':
    setting = {
        "username": "zhanghui",
        "password": "123456",
    }
    tx = Transmitter(setting.get("username", None), setting.get("password", None))
    client = tx.connect_ws()
    time.sleep(5)
    assert client == tx.client
    client.send("mmmmmmmmmmmmmmmmm")
