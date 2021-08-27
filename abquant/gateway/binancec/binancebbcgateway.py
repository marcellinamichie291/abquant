
from abquant.event.dispatcher import EventDispatcher
from .binancecgateway import BinanceCGateway


class BinanceBBCGateway(BinanceCGateway):
    def __init__(self, event_dispatcher: EventDispatcher):
        super().__init__(event_dispatcher)
        self.set_gateway_name("BINANCEBBC")
    
    def ustd_based() -> bool:
        return False