import os
import time
from typing import Dict, List
from enum import Enum
import logging

from abquant.trader.common import OrderType, Direction, Offset, Exchange
from abquant.trader.object import CancelRequest, OrderRequest, PositionData, OrderData
from abquant.gateway import BitmexGateway, Gateway, BinanceUBCGateway, BinanceBBCGateway, BinanceSGateway, DydxGateway, BybitBBCGateway, BybitUBCGateway
from abquant.event import EventDispatcher, EventType, Event
from abquantui.encryption import decrypt
from abquantui.common import *


class ExchangeOperation:
    """
        exchange operations lib
    """
    def __init__(self, config: Dict):
        self._config = config
        self._logger = logging.getLogger('ExchangeOperation')
        self._logger.setLevel(logging.INFO)
        self._event_dispatcher = None   # 单dispatcher的前提：账户间gateway不同
        self.gateways: Dict[str: Gateway] = {}
        self._gateway_second_limits: Dict[str: int] = {}
        self._gateway_minute_limits: Dict[str: int] = {}
        self.__start()

    def __start(self):
        if self.gateways:
            return
        self._event_dispatcher = EventDispatcher(interval=1)
        opconf = self._config.get('operation')
        accounts = opconf.get('accounts')
        for account in accounts:
            account_name = account.get('name')
            if not account_name:
                raise Exception('ExchangeOperation: No account name specified')
            gateways = account.get('gateways')
            if not gateways:
                raise Exception('ExchangeOperation: No gateway name(s) specified')
            encrypt_key = account.get('encrypt_key')
            encrypt_secret = account.get('encrypt_secret')
            if not encrypt_key or not encrypt_secret:
                raise Exception('ExchangeOperation: No encrypt key or secret specified')
            isprod = account.get('is_prod')
            for gateway_name in gateways.split(','):
                gateway_setting = {
                    'encrypt_key': encrypt_key,
                    'encrypt_secret': encrypt_secret,
                    'proxy_host': None if is_prod() else PROXY_HOST,
                    'proxy_port': 0 if is_prod() else PROXY_PORT,
                    "test_net": ["TESTNET", "REAL"][1 if isprod else 0]
                }
                self.__connect_gateway(account_name, gateway_name, gateway_setting)
                self._gateway_second_limits.update({gateway_name: SECOND_RATE_LIMITS.get(GatewayName(gateway_name))})
                self._gateway_minute_limits.update({gateway_name: MINUTE_RATE_LIMITS.get(GatewayName(gateway_name))})
        self._info('gateways started')

    def __connect_gateway(self, account_name: str, gateway_name: str, conf: Dict):
        if len(self.gateways) > 0:
            return '\n gateways not empty, do nothing, existed -> {}'.format(self.gateways.keys())
        abpwd = os.getenv("ABPWD", "abquanT%go2moon!")
        gkey = self.gateway_key(account_name, gateway_name)
        cls = SUPPORTED_GATEWAY.get(GatewayName(gateway_name))
        if not cls:
            raise Exception('ExchangeOperation: No gateway class found in supported gateways')
        if 'encrypt_key' in conf and 'encrypt_secret' in conf:
            try:
                conf['key'] = decrypt(conf['encrypt_key'], abpwd)
                conf['secret'] = decrypt(conf['encrypt_secret'], abpwd)
                conf.pop('encrypt_key')
                conf.pop('encrypt_secret')
            except Exception as e:
                self.error(f'Error occurs when decrypting key and secret for gateway {gateway_name}')
                raise e
        else:
            raise Exception('ExchangeOperation: No encrypt key or secret specified')
        self._info(f'connect gateway start {gateway_name} for account {account_name}')
        gw = cls(self._event_dispatcher)
        gw.connect(conf)
        self.gateways[gkey] = gw
        time.sleep(10)
        self._info(f'connect gateway end {gateway_name} for account {account_name}')

    def _info(self, msg):
        self._logger.info(msg)

    @staticmethod
    def gateway_key(account_name, gateway_name):
        if not account_name and not gateway_name:
            return None
        elif not account_name:
            return gateway_name
        else:
            return account_name + '.' + gateway_name

    def clear_position_list(self, account_name: str, gateway_name: str, position_list: List[PositionData]):
        """
            清仓，position列表全部清仓
        """
        if not account_name or not gateway_name or not position_list:
            raise Exception('ExchangeOperation: clear_position_list: parameter incorrect')
        for position in position_list:
            self.clear_position(account_name, gateway_name, position)

    def clear_position_by_symbol(self, account_name: str, gateway_name: str, position_list: List[PositionData], symbol: str):
        """
            清仓，只清symbol指定仓位
        """
        if not account_name or not gateway_name or not position_list or not symbol:
            raise Exception('ExchangeOperation: clear_position_by_symbol: parameter incorrect')
        for position in position_list:
            if position.symbol != symbol:
                continue
            self.clear_position(account_name, gateway_name, position)

    def clear_position(self, account_name: str, gateway_name: str, position: PositionData):
        """
            清仓
        """
        if not account_name or not gateway_name or not position:
            raise Exception('ExchangeOperation: clear_position: parameter incorrect')
        if position.volume == 0:
            return
        if gateway_name != position.gateway_name:
            self._info(
                f'clear_position: gateway name conflict, {gateway_name} - {position.gateway_name}')
        gateway = self.gateways.get(self.gateway_key(account_name, gateway_name))
        if not gateway:
            raise Exception(f"Warning: no gateway [{account_name}.{gateway_name}] found for position, do nothing")
        direction = Direction.LONG if position.volume < 0 else Direction.SHORT
        ab_orderid = self.send_order(account_name, gateway_name, position.symbol,
                                                                 position.price, abs(position.volume),
                                                                 direction, Offset.CLOSE, OrderType.MARKET)
        self._info(f"clear_position: position [{gateway_name} {position.symbol} {position.volume}] called to CLEAR !\n"
                   f"clear_position: client order id: {ab_orderid}")

    def cancel_order_list(self, account_name: str, gateway_name: str, order_list: List[OrderData], symbol: str = None):
        """
            撤销订单列表
        """
        if not account_name or not gateway_name or not order_list:
            raise Exception('ExchangeOperation: cancel_order_list: parameter incorrect')
        second_limit = self._gateway_second_limits[gateway_name]
        minute_limit = self._gateway_minute_limits[gateway_name]
        second_num = 0
        minute_num = 0
        for order in order_list:
            if symbol and symbol != order.symbol:
                continue
            if gateway_name != order.gateway_name:
                self._info(
                    f'cancel_order_list: gateway name conflict, {gateway_name} - {order.gateway_name}')
            gateway = self.gateways.get(self.gateway_key(account_name, gateway_name))
            if not gateway:
                raise Exception(
                  f"Warning: cancel_order_list: no gateway [{account_name}.{gateway_name}] found for order, do nothing")
                continue
            # 交易所流量控制
            second_num += 1
            minute_num += 1
            if second_num > second_limit:
                self._info(f"gateway {gateway_name} exceed second limit {second_limit}, sleep 10 secs")
                time.sleep(10)
                second_num = 0
            if minute_num > minute_limit:
                self._info(f"gateway {gateway_name} exceed minute limit {minute_limit}, sleep 60 secs")
                time.sleep(60)
                minute_num = 0
            req = order.create_cancel_request()
            gateway.cancel_order(req)
            self._info(f"cancel_order_list: order [{gateway_name} {order.symbol} {order.volume} {order.direction} "
                  f"{order.orderid}] called to CANCEL !")
        return

    def send_order(self, account_name, gateway_name, symbol: str,
                         price: float, volume: float,
                         direction: Direction, offset: Offset, order_type: OrderType) -> List[str]:
        """
            发送订单
        """
        gateway = self.gateways.get(self.gateway_key(account_name, gateway_name))
        exchange = gateway.exchanges[0]
        req = OrderRequest(
                symbol=symbol,
                exchange=exchange,
                direction=direction,
                offset=offset,
                type=order_type,
                price=price,
                volume=abs(volume)
            )
        ab_orderids = gateway.send_order(req)
        return ab_orderids

    def buy(self, account_name, gateway_name, symbol: str, price: float, volume: float,
                                              order_type: OrderType = OrderType.MARKET) -> List[str]:
        """
            开多
            单向持仓下可平空
        """
        return self.send_order(account_name, gateway_name, symbol, price, volume,
                                                           Direction.LONG, Offset.OPEN, order_type)

    def short(self, account_name, gateway_name, symbol: str, price: float, volume: float,
                                                order_type: OrderType = OrderType.MARKET) -> List[str]:
        """
            开空
            单向持仓下可平多
        """
        return self.send_order(account_name, gateway_name, symbol, price, volume,
                                                           Direction.SHORT,  Offset.OPEN, order_type)

    def cancel_order(self, account_name, order: OrderData):
        """
            取消订单
        """
        gateway_name = order.gateway_name
        gateway = self.gateways.get(self.gateway_key(account_name, gateway_name))
        req = order.create_cancel_request()
        gateway.cancel_order(req)


if __name__ == '__main__':
    _config = {'operation': {
        'accounts': [{
            'name': 'test',
            'gateways': 'BITMEX',
            'encrypt_key': 'dBdHxAr9HJi7Iv1P+XDWU3rDjz1bvo/zghVWCdjk7pI=',
            'encrypt_secret': 'ufRYzjzIZ/30+6zdK+DI8dccrWOhLFhal1LGrlIgW9XYNhf7muQRvccOx6rS9Emf',
            'is_prod': False
        }]
    }}
    exo = ExchangeOperation(_config)
    _ab_orderids = exo.buy('test', 'BITMEX', 'XBTUSD', 37000.0, 100.0, OrderType.LIMIT)
    print(_ab_orderids)

    # time.sleep(5)
    #
    # _gateway = exo.gateways.get(exo.gateway_key('test', 'BITMEX'))
    # # clear position -------------------
    # _position_list = []
    # _positions = _gateway.event_dispatcher.order_manager.positions
    # for _, _order in _positions.items():
    #     _position_list.append(_order)
    # exo.clear_position_list('test', 'BITMEX', _position_list, 'ETHUSD')
    # # cancel order ----------------------
    # _order_list = []
    # _orders = _gateway.event_dispatcher.order_manager.orders
    # for _, _order in _orders.items():
    #     _order_list.append(_order)
    # exo.cancel_order_list('test', 'BITMEX', _order_list, 'XBTUSD')
