from enum import IntEnum, auto


class EventType(IntEnum):
    EVENT_TIMER = auto()
    EVENT_TICK = auto()
    EVENT_TRANSACTION = auto()
    EVENT_ENTRUST = auto()
    EVENT_DEPTH = auto()
    EVENT_TRADE = auto()
    EVENT_ORDER = auto()
    EVENT_POSITION = auto()
    EVENT_ACCOUNT = auto()
    EVENT_CONTRACT = auto()
    EVENT_LOG = auto()
    EVENT_EXCEPTION = auto()
    EVENT_GATEWAY = auto()
