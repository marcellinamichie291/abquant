import time
from abc import ABC, abstractmethod
from typing import Dict, List

from abquant.event import EventDispatcher
from abquant.gateway import BitmexGateway, Gateway, BinanceUBCGateway, BinanceBBCGateway, BinanceSGateway, DydxGateway
from abquant.monitor import Monitor
from abquant.strategytrading import LiveStrategyRunner
import logging

from typing import TYPE_CHECKING

from abquantui.config_helpers import yaml_config_to_str

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class GatewayName:
    BITMEX = 'BITMEX'
    BINANCEUBC = 'BINANCEUBC'
    BINANCEBBC = 'BINANCEBBC'
    BINANCES = 'BINANCES',
    DYDX = 'DYDX'


SUPPORTED_GATEWAY = {
    GatewayName.BITMEX: BitmexGateway,
    GatewayName.BINANCEUBC: BinanceUBCGateway,
    GatewayName.BINANCEBBC: BinanceBBCGateway,
    GatewayName.BINANCES : BinanceSGateway,
    GatewayName.DYDX : DydxGateway
}


class StrategyLifecycle(ABC):

    def __init__(self, config: Dict, app: 'AbquantApplication' = None):
        self.app = app
        self._config = config
        self._event_dispatcher: EventDispatcher = EventDispatcher(interval=config.get('interval', 1))
        logging.info('EventDispatcher started')
        self._live_strategy_runner: LiveStrategyRunner
        common_setting = {
            "log_path": self._config.get('log_path'),
        }

        monitor = Monitor(common_setting)
        monitor.start()

        self._strategy_runner = LiveStrategyRunner(self._event_dispatcher)
        self._strategy_runner.set_monitor(monitor)
        logging.info('LiveStrategyRunner init')
        self.gateways: Dict[str: Gateway] = {}

    def connect_gateway(self):
        if len(self.gateways) > 0:
            return '\n gateways not empty, do nothing, existed -> {}'.format(self.gateways.keys())
        for name, cls in SUPPORTED_GATEWAY.items():
            conf = self._config.get('gateway').get(name)
            if conf:
                logging.info('connect gateway start: %s', name)
                gw = cls(self._event_dispatcher)
                gw.connect(conf)
                self.gateways[name] = gw
                time.sleep(15)
                logging.info('connect gateway end: %s', name)
        if len(self.gateways) > 0:
            self.add_init_strategy()
            time.sleep(10)
            logging.info('add_init_strategy is called')
            return '\n gateways inited -> {}'.format(self.gateways.keys())
        else:
            return '\n no gateway inited'

    def start(self):
        if len(self.gateways) < 1:
            logging.error('no gateway is connected, connect gateway first!')
            return
        if len(self._strategy_runner.strategies) < 1:
            logging.error('no strategy is added, implement add_init_strategy method first!')
        self._strategy_runner.start_all_strategies()

    def stop(self):
        self._strategy_runner.stop_all_strategies()

    def status(self):
        return str(self._strategy_runner.strategies.keys())

    @abstractmethod
    def add_init_strategy(self):
        pass

    def config(self) -> str:
        return yaml_config_to_str(self._config)

