import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List

from abquant.event import EventDispatcher, EventType
from abquant.gateway import BitmexGateway, Gateway, BinanceUBCGateway, BinanceBBCGateway, BinanceSGateway, DydxGateway, BybitBBCGateway, BybitUBCGateway
from abquant.monitor import Monitor
from abquant.strategytrading import LiveStrategyRunner
import logging

from typing import TYPE_CHECKING

from abquantui.config_helpers import yaml_config_to_str
from abquantui.encryption import encrypt, decrypt


if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class GatewayName:
    BITMEX = 'BITMEX'
    BINANCEUBC = 'BINANCEUBC'
    BINANCEBBC = 'BINANCEBBC'
    BINANCES = 'BINANCES',
    DYDX = 'DYDX'
    BYBITBBC = 'BYBITBBC'
    BYBITUBC = 'BYBITUBC'


SUPPORTED_GATEWAY = {
    GatewayName.BITMEX: BitmexGateway,
    GatewayName.BINANCEUBC: BinanceUBCGateway,
    GatewayName.BINANCEBBC: BinanceBBCGateway,
    GatewayName.BINANCES: BinanceSGateway,
    GatewayName.DYDX: DydxGateway,
    GatewayName.BYBITUBC: BybitUBCGateway,
    GatewayName.BYBITBBC: BybitBBCGateway
}


class StrategyLifecycle(ABC):

    def __init__(self, config: Dict, app: 'AbquantApplication' = None):
        self.app = app
        self._config = config
        self._event_dispatcher: EventDispatcher = EventDispatcher(interval=config.get('interval', 1))
        logging.info('EventDispatcher started')
        common_setting = {
            "log_path": self._config.get('log_path') if 'lark_url' in config else None,
            "lark_url": self._config.get('lark_url') if 'lark_url' in config else None,
        }

        monitor = Monitor(common_setting, disable_logger=True)
        monitor.start()

        self._strategy_runner = LiveStrategyRunner(self._event_dispatcher)
        self._strategy_runner.set_monitor(monitor)
        logging.info('LiveStrategyRunner init')
        self.gateways: Dict[str: Gateway] = {}

    @property
    def strategy_runner(self):
        return self._strategy_runner

    @property
    def event_dispatcher(self):
        return self.event_dispatcher

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, new_config: Dict):
        if new_config:
            self._config = new_config
            logging.info('config updated')

    def connect_gateway(self):
        if len(self.gateways) > 0:
            return '\n gateways not empty, do nothing, existed -> {}'.format(self.gateways.keys())
        abpwd = os.getenv("ABPWD", "abquanT%go2moon!")
        for name, cls in SUPPORTED_GATEWAY.items():
            conf = self._config.get('gateway').get(name)
            if conf:
                if 'key' in conf and 'secret' in conf:
                    pass
                elif 'encrypt_key' in conf and 'encrypt_secret' in conf:
                    try:
                        conf['key'] = decrypt(conf['encrypt_key'], abpwd)
                        conf['secret'] = decrypt(conf['encrypt_secret'], abpwd)
                        conf.pop('encrypt_key')
                        conf.pop('encrypt_secret')
                    except Exception as e:
                        logging.error(f'Error occurs when decrypting key and secret for gateway {name}')
                        continue
                else:
                    logging.info(f'Error: no (encrypted) key and secret config for gateway {name}')
                    continue
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

    def command_config(self) -> str:
        """
        called by ui command config,and must return a str
        """
        return yaml_config_to_str(self._config)
