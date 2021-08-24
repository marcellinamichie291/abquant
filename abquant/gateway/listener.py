import json
import logging
import socket
import ssl
import sys
import traceback
from datetime import datetime
from threading import Lock, Thread
from time import sleep
from abc import ABC, abstractmethod, abstractstaticmethod
from typing import Dict, Optional

import websocket

from .basegateway import Gateway
from abquant.trader.utility import get_file_logger


class WebsocketListener(ABC):
    """
    
     为后续可能存在的 dex 交易所（非websocket API ）流出 基类Listener 的空间。
    Websocket API

    """

    def __init__(self, gateway: Gateway):


        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

        self.host = None

        self._ws_lock = Lock()
        self._ws = None

        self._worker_thread = None
        self._ping_thread = None
        self._active = False

        self.proxy_host = None
        self.proxy_port = None
        self.ping_interval = 60 
        self.header = {}

        self.logger: Optional[logging.Logger] = None

        # For debugging
        self._last_sent_text = None
        self._last_received_text = None

    def init(self,
             host: str,
             proxy_host: str = "",
             proxy_port: int = 0,
             ping_interval: int = 60,
             header: dict = None,
             log_path: Optional[str] = None,
             ):
        """
        log_path: it is ok to be set to '/dev/stdou' for debugging
        """
        self.host = host
        self.ping_interval = ping_interval  # seconds
        if log_path is not None:
            self.logger = get_file_logger(log_path)
            self.logger.setLevel(logging.DEBUG)

        if header:
            self.header = header

        if proxy_host and proxy_port:
            self.proxy_host = proxy_host
            self.proxy_port = proxy_port

    def start(self):
        """
        Start the client and on_connected function is called after webscoket
        is connected succesfully.

        Please don't send packet untill on_connected fucntion is called.
        """

        self._active = True
        self._worker_thread = Thread(target=self._run)
        self._worker_thread.start()

        self._ping_thread = Thread(target=self._run_ping)
        self._ping_thread.start()

    def stop(self):
        self._active = False
        self._disconnect()

    def join(self):
        self._ping_thread.join()
        self._worker_thread.join()

    def send_packet(self, packet: dict):
        text = json.dumps(packet)
        self._record_last_sent_text(text)
        return self._send_text(text)

    def _log(self, msg, *args):
        logger = self.logger
        if logger:
            logger.debug(msg, *args)

    def _send_text(self, text: str):
        ws = self._ws
        if ws:
            ws.send(text, opcode=websocket.ABNF.OPCODE_TEXT)
            self._log('sent text: %s', text)

    def _send_binary(self, data: bytes):
        ws = self._ws
        if ws:
            ws.send(data,  opcode=websocket.ABNF.OPCODE_BINARY)
            self._log('sent binary: %s', data)

    def _create_connection(self, *args, **kwargs):
        #TODO maybe it is ok to disable  lock for thread-safe, it is required to combine run_ping with run.
        return websocket.create_connection(*args, **kwargs)

    def _ensure_connection(self):
        triggered = False
        with self._ws_lock:
            if self._ws is None:
                self._ws = self._create_connection(
                    self.host,
                    sslopt={"cert_reqs": ssl.CERT_NONE},
                    http_proxy_host=self.proxy_host,
                    http_proxy_port=self.proxy_port,
                    header=self.header
                )
                triggered = True
        if triggered:
            self.on_connected()

    def _disconnect(self):
        """
        """
        triggered = False
        with self._ws_lock:
            if self._ws:
                ws: websocket.WebSocket = self._ws
                self._ws = None

                triggered = True
        if triggered:
            ws.close()
            self.on_disconnected()

    def _run(self):
        try:
            while self._active:
                try:
                    self._ensure_connection()
                    ws = self._ws
                    if ws:
                        text = ws.recv()

                        # ws object is closed when recv function is blocking
                        if not text:
                            self._disconnect()
                            continue

                        self._record_last_received_text(text)

                        try:
                            data = self.unpack_data(text)
                        except ValueError as e:
                            print("websocket unable to parse data: " + text)
                            raise e

                        self._log('recv data: %s', data)
                        self.on_packet(data)
                # ws is closed before recv function is called
                # For socket.error
                except (
                    websocket.WebSocketConnectionClosedException,
                    websocket.WebSocketBadStatusException,
                    socket.error
                ):
                    self._disconnect()

                # other internal exception raised in on_packet
                except:  # noqa
                    et, ev, tb = sys.exc_info()
                    self.on_error(et, ev, tb)
                    self._disconnect()
        except:  # noqa
            et, ev, tb = sys.exc_info()
            self.on_error(et, ev, tb)
        self._disconnect()

    @staticmethod
    def unpack_data(data: str) -> Dict:
        return json.loads(data)

    def _run_ping(self):
        while self._active:
            try:
                self._ping()
            except:  # noqa
                et, ev, tb = sys.exc_info()
                self.on_error(et, ev, tb)
                sleep(1)

            for i in range(self.ping_interval):
                if not self._active:
                    break
                sleep(1)

    def _ping(self):
        ws = self._ws
        if ws:
            ws.send("ping", websocket.ABNF.OPCODE_PING)

    @staticmethod
    @abstractmethod
    def on_connected():
        """
        Callback when websocket is connected successfully.
        """
        pass

    @staticmethod
    @abstractmethod
    def on_disconnected():
        """
        Callback when websocket connection is lost.
        """
        pass

    @staticmethod
    @abstractmethod
    def on_packet(packet: dict):
        pass

    def on_error(self, exception_type: type, exception_value: Exception, tb):
        exception_detail = self.exception_detail(exception_type, exception_value, tb)

        sys.stderr.write(exception_detail)
        # TODO exception event.
        return sys.excepthook(exception_type, exception_value, tb)

    def exception_detail(
        self, exception_type: type, exception_value: Exception, tb
    ):
        text = "[{}]: Unhandled WebSocket Error:{}\n".format(
            datetime.now().isoformat(), exception_type
        )
        text += "LastSentText:\n{}\n".format(self._last_sent_text)
        text += "LastReceivedText:\n{}\n".format(self._last_received_text)
        text += "Exception trace: \n"
        text += "".join(
            traceback.format_exception(exception_type, exception_value, tb)
        )
        return text

    def _record_last_sent_text(self, text: str):
        self._last_sent_text = text[:1000]

    def _record_last_received_text(self, text: str):
        self._last_received_text = text[:1000]
