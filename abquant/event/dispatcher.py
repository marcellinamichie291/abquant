
from collections import defaultdict
from queue import Empty, Queue
from threading import Thread
import time
from typing import Any, Callable, List

from .event import EventType
from abquant.trader.exception import CongestionException


class Event:

    def __init__(self, type: EventType, data: Any = None):
        """"""
        self.type = type
        self.data = data


HandlerType = Callable[[Event], None]


class EventDispatcher:

    def __init__(self, event_threshold: int = 100, interval: int = 1):
        self._interval: int = interval
        self._event_threshold = event_threshold
        self._queue: Queue = Queue()
        self._active: bool = False
        self._thread: Thread = Thread(target=self._run)
        self._timer: Thread = Thread(target=self._run_timer)
        self._handlers: defaultdict = defaultdict(list)
        self._general_handlers: List = []

        # TODO  warning. start before all handler registered may cause race condition in self._randlers
        self.start()

    def _run(self) -> None:
        while self._active:
            try:
                event = self._queue.get(block=True, timeout=1)
                self._process(event)
            except Empty:
                pass

    def _process(self, event: Event) -> None:
        if event.type in self._handlers:
            [handler(event) for handler in self._handlers[event.type]]

        if self._general_handlers:
            [handler(event) for handler in self._general_handlers]

    def _run_timer(self) -> None:
        while self._active:
            time.sleep(self._interval)
            event = Event(type=EventType.EVENT_TIMER, data=self._interval)
            self.put(event)
            self.check_event_congestion()

    def start(self) -> None:
        self._active = True
        self._thread.start()
        self._timer.start()

    def stop(self) -> None:
        self._active = False
        self._timer.join()
        self._thread.join()

    def put(self, event: Event) -> None:
        self._queue.put(event)

    def register(self, type: str, handler: HandlerType) -> None:
        handler_list = self._handlers[type]
        if handler not in handler_list:
            handler_list.append(handler)

    def unregister(self, type: str, handler: HandlerType) -> None:
        handler_list = self._handlers[type]

        if handler in handler_list:
            handler_list.remove(handler)

        if not handler_list:
            self._handlers.pop(type)

    def register_general(self, handler: HandlerType) -> None:
        if handler not in self._general_handlers:
            self._general_handlers.append(handler)

    def unregister_general(self, handler: HandlerType) -> None:
        if handler in self._general_handlers:
            self._general_handlers.remove(handler)

    def check_event_congestion(self) -> bool:
        congested_event = self._queue.qsize()
        if congested_event > self._event_threshold:
            self._queue.put(Event(type=EventType.EVENT_EXCEPTION, data=CongestionException(
                threshold=self._event_threshold, congested_event=congested_event)))
            # TODO log here. at least warning level
