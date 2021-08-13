

class OrderException(Exception):
    pass


class MarketException(Exception):
    pass


class CongestionException(Exception):
    def __init__(self, threshold, message=r'Warning: the event congested in evend dispatcher is more than the threshold {} set. \
        Must you check any time-consuming operation or sync IO operation may used in your strategy implementation.'):
        self.threshold = threshold
        self.message = message.format(self.threshold)
        super(CongestionException, self).__init__(self.message)
