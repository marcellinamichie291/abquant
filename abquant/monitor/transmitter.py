
import time
import json
import _thread
import requests

import websocket

from . import LOGIN_URL, WS_URL


class Transmitter:

    client = None

    def __init__(self):
        pass

    def init_ws(self, username, password):
        if self.client is not None:
            return self.client
        payload = {}
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        if username is None or password is None:
            return
        login_url = LOGIN_URL + "?userName=" + username + "&password=" + password
        try:
            response = requests.request("GET", login_url, headers=headers, data=payload)
            jn = json.load(response)
        except Exception:
            return

        access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MzY3MDU3MjgsImlkIjoxMCwidXNlck5hbWUiOiJ5YXFpYW5nIn0.TRZPoUiJqAwk6j68Sv_h4GVnKRkdoMTCddumSLCzVpc"
        websocket.enableTrace(True)
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