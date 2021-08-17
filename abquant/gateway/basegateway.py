from abc import ABC, abstractmethod
from abquant.event import EventDispatcher

class Gateway(ABC):
    def __init__(self, event_dispatcher: EventDispatcher):
        pass
    
    @abstractmethod
    def subscribe(self, ab_symbol):
        pass