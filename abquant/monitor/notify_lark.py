from queue import Queue, Empty
from threading import Thread
from enum import Enum
from typing import Dict, List
import logging, requests, json


class TypeEnum(Enum):
    TEXT = 'text'
    POST = 'post'


class LarkMessage:
    """
    if text message, pass text

    if post message, pass title and content
    """

    def __init__(self, owner: str, url, type: TypeEnum, text: str = None, title: str = None, content: List = None):
        self.owner = owner
        self.url: str = url
        self.type: TypeEnum = type
        self.text: str = text
        self.title: str = title
        self.content: List = content

    def __str__(self):
        return str(vars(self))


def _build_for_lark(msg: LarkMessage):
    if not msg:
        return
    res: Dict = None
    if msg.type == TypeEnum.TEXT:
        res = {
            'msg_type': msg.type.value,
            'content': {
                'text': msg.text
            }
        }
    elif msg.type == TypeEnum.POST:
        res = {
            'msg_type': msg.type.value,
            'content': {
                "post": {
                    "zh_cn": {
                        "title": msg.title,
                        "content": msg.content
                    }
                }
            }
        }
    if res:
        return res
    else:
        return None


class NotifyLark:

    def __init__(self, queue_size: int = 1000):
        self._logger = logging.getLogger(__name__)
        self._queue: Queue = Queue(queue_size)
        self._active: bool = False
        self._thread: Thread = Thread(target=self._run, name="NotifyLarkThread", daemon=True)
        self._start()

    def _run(self) -> None:
        while self._active:
            try:
                msg: LarkMessage = self._queue.get(block=True, timeout=10)
                self._process(msg)
            except Empty:
                pass

    def _process(self, msg: LarkMessage) -> None:

        try:
            to_send = _build_for_lark(msg)
            self._logger.info('send_to_lark: %s %s', msg.owner, to_send)
            print('send to lark')
            requests.post(msg.url, json=_build_for_lark(msg))
        except Exception as e:
            self._logger.error(exc_info=e)

    def _start(self) -> None:
        self._active = True
        self._thread.start()
        self._logger.info('LarkNotify started')

    def stop(self) -> None:
        self._active = False
        self._thread.join()

    def put(self, msg: LarkMessage) -> None:
        if self._queue.full():
            self._logger.error('queue is full, discard msg %s:', msg)
        else:
            self._queue.put(msg)


def buildText(label, value):
    return [{'tag': 'text', 'text': "{}：{}".format(label, value)}]


notify_lark = NotifyLark()
logging.info('notify_lark inited')
