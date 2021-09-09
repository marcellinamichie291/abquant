
from abquant.event.dispatcher import EventDispatcher
from .binancecgateway import BinanceCGateway


class BinanceUBCGateway(BinanceCGateway):
    def __init__(self, event_dispatcher: EventDispatcher):
        super().__init__(event_dispatcher)
        self.set_gateway_name("BINANCEUBC")
    
    def ustd_based(self) -> bool:
        return True