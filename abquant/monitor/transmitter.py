
import time
import json
from threading import Thread
import requests

import websocket

from .util import MLogger

LOGIN_URL = "https://dct-test001.wecash.net/dct-business-api/login"
WS_URL = "wss://dct-test001-internal.wecash.net/dct-service-abquant/ws/business?access_token="
MAX_CONNECT_RETRY = 5


class Transmitter:

    client = None
    username = None
    password = None

    def __init__(self, setting: dict):
        if setting is None:
            return
        self.username = setting.get("username", None)
        self.password = setting.get("password", None)
        self._pp_thread = None  # underlying ping/pong thread

    def connect_ws(self):
        if self.client is not None:
            return self.client
        payload = {}
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        if self.username is None or self.password is None:
            MLogger.log("监控：初始化：用户名或密码不存在")
            return
        login_url = LOGIN_URL + "?userName=" + self.username + "&password=" + self.password
        access_token = None
        try:
            response = requests.request("GET", login_url, headers=headers, data=payload)
            jn = json.loads(response.text)
            access_token = jn.get("data").get("access_token")
            # MLogger.log(access_token)
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
        MLogger.log("tx: start ping/pong thread")
        time.sleep(1)

        return ws

    def stop(self):
        pass

    def run_forever(self, ws):
        MLogger.log("tx: run forever\n")
        if self.client is None:
            MLogger.log("Error: tx: no client to run ping pong thread")
            return
        self.client.run_forever(ping_interval=5, ping_timeout=3)

    def send(self, data):
        if self.client is None:
            MLogger.log("Error: tx: websocket client is none")
            raise Exception("websocket client is none")
        if isinstance(data, (int, float)):
            data = str(data)
        elif isinstance(data, (list, tuple, set)):
            data = str(data)
        elif isinstance(data, dict):
            data = json.dumps(data)
        else:
            pass
        self.client.send(data)

    def on_message(self, ws, msg):
        MLogger.log(msg)

    def on_error(self, ws, error):
        MLogger.error(error)

    def on_open(self, ws):
        self.client = ws
        MLogger.info("tx: open")

    def on_close(self, ws, b, c):
        MLogger.info("tx: close")
        self.client = None
        i = 1
        time.sleep(3)
        while i <= MAX_CONNECT_RETRY:
            self.client = self.connect_ws()
            time.sleep(i * 2)
            if self.client is not None:
                break
            i += 1
        MLogger.info(f"tx: Reconnect after {i} retries")

    def on_ping(self, pingMsg, ex):
        # ws._send_ping()
        MLogger.log("tx: ping")

    def on_pong(self, pongMsg, ex):
        # MLogger.log("tx: pong")
        pass


if __name__ == '__main__':
    setting = {
        "username": "zhanghui",
        "password": "123456",
    }
    tx = Transmitter(setting)
    client = tx.connect_ws()
    time.sleep(5)
    assert client == tx.client
    client.send("mmmmmmmmmmmmmmmmm")
