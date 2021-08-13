

class OrderException(Exception):
    pass


class MarketException(Exception):
    pass


class CongestionException(Exception):
    def __init__(self, threshold: int, congested_event: int, message: str = r'Warning: the number of event congested in evend dispatcher is now {} more than the threshold {} set. \
        Must you check any time-consuming operation or sync IO operation may used in your strategy implementation.'):
        self.threshold = threshold
        self.congested_event = congested_event
        self.message = message.format(self.congested_event,self.threshold)
        super(CongestionException, self).__init__(self.message)
