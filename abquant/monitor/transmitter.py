
import time
import json
import _thread
import requests

import websocket

# from . import LOGIN_URL, WS_URL
LOGIN_URL = "https://dct-test001.wecash.net/dct-business-api/login"
WS_URL = "ws://dct-test001.wecash.net/dct-business-api/ws/business?access_token="


class Transmitter:

    client = None
    username = None
    password = None

    def __init__(self, setting: dict):
        if setting is None:
            return
        self.username = setting.get("username", None)
        self.password = setting.get("password", None)
        # self.init_ws(username, password)

    def init_ws(self):
        if self.client is not None:
            return self.client
        payload = {}
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        if self.username is None or self.password is None:
            return
        login_url = LOGIN_URL + "?userName=" + self.username + "&password=" + self.password
        #access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MzY3MDU3MjgsImlkIjoxMCwidXNlck5hbWUiOiJ5YXFpYW5nIn0.TRZPoUiJqAwk6j68Sv_h4GVnKRkdoMTCddumSLCzVpc"
        access_token = None
        try:
            response = requests.request("GET", login_url, headers=headers, data=payload)
            jn = json.loads(response.text)
            access_token = jn.get("data").get("access_token")
        except Exception:
            return

        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(WS_URL + access_token, on_message=self.on_message, on_error=self.on_error,
                                    on_close=self.on_close, on_open=self.on_open,
                                    on_ping=self.on_ping, on_pong=self.on_pong)
        # ws.run_forever(ping_interval=30, ping_timeout=5)
        _thread.start_new_thread(self.run_forever, (ws,))
        time.sleep(1)

        return self.client

    def on_message(self, ws, msg):
        print(msg)

    def on_error(self, ws, error):
        print(error)

    def on_open(self, ws):
        global wsClient
        wsClient = ws
        self.client = ws
        print("open")


    def on_close(ws, close_status_code, close_msg):
        print("close")


    def on_ping(ws, pingMsg):
        #ws._send_ping()
        print("ping")


    def on_pong(ws, pongMsg):
        print("pong")

    def run_forever(ws):
        ws.run_forever(ping_interval=10, ping_timeout=5)



if __name__ == "__main__":
    #global wsClient
    for i in range(10):
        wsClient.send(f'client message {i}')
        print(f'client message {i}')
        value = wsClient.recv()
        print(value)
        time.sleep(1)