from abquant.event.dispatcher import EventDispatcher
from .bybit_gateway import BybitGateway

class BybitUBCGateway(BybitGateway):
    def __init__(self, event_dispatcher: EventDispatcher):
        super().__init__(event_dispatcher)
        self.set_gateway_name("BYBITUBC")
        