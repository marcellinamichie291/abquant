from logging import LoggerAdapter
from typing import Dict, List

from abquant.trader.msg import OrderData, TradeData
from abquant.trader.object import LogData

class DummyMonitor:
    def send_order(self, run_id, order: OrderData):
        pass

    def send_trade(self, run_id, trade: TradeData):
        pass

    def send_position(self, run_id, ab_symbol: str, pos: float):
        pass

    def send_parameter(self, run_id, parameters: Dict):
        pass

    def send_variable(self, run_id, variables: Dict):
        pass

    def send_log(self, run_id, log: LogData, log_type: str='custom'):
        pass

    def send_status(self, run_id, status_type: str, ab_symbols: List[str]):
        pass
