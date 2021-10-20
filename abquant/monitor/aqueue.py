from abc import ABC
import asyncio
import websocket
import time
import _thread


class AsyncQueue:

    queue = None

    def __init__(self):
        if self.queue is None:
            self.queue = asyncio.Queue(maxsize=1000)

    async def write(self):
        pass

