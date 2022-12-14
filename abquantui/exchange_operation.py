import logging
import time
import json
from enum import Enum
from typing import Dict, List
from datetime import datetime
from dataclasses import dataclass
from copy import copy

from abquant.event import EventDispatcher, EventType
from abquant.gateway import Gateway
from abquant.trader.common import OrderType, Direction, Offset, Status
from abquant.trader.object import OrderRequest, PositionData, OrderData, AccountData
from abquantui.common import *
from abquantui.encryption import decrypt


class ExchangeOperation:
    """
        exchange operations lib
    """
    def __init__(self, config: Dict):
        self._config = config
        self._logger = logging.getLogger('ExchangeOperation')
        self._logger.setLevel(logging.INFO)
        self._event_dispatcher = None   # 单dispatcher的前提：账户间gateway不同
        self.orders: Dict = {}
        self.gateways: Dict[str: Gateway] = {}
        self._gateway_second_limits: Dict[str: int] = {}
        self._gateway_minute_limits: Dict[str: int] = {}
        self.key_is_valid = False   # dict if multiple account
        self.__start()

    def __start(self):
        if self.gateways:
            return
        self._event_dispatcher = EventDispatcher(interval=1)
        self._event_dispatcher.register(EventType.EVENT_ORDER, self._on_order)
        self._event_dispatcher.register(EventType.EVENT_ACCOUNT, self._on_account)
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
                gateway_name = gateway_name.strip()
                gateway_setting = dict(copy(account))
                gateway_setting.pop('name')
                gateway_setting.pop('gateways')
                gateway_setting.update({"test_net": ["TESTNET", "REAL"][1 if isprod else 0]})
                self.__connect_gateway(account_name, gateway_name, gateway_setting)
                self._gateway_second_limits.update({gateway_name: SECOND_RATE_LIMITS.get(gateway_name)})
                self._gateway_minute_limits.update({gateway_name: MINUTE_RATE_LIMITS.get(gateway_name)})
            if not self.key_is_valid:
                raise Exception('ExchangeOperation: gateway not connected, check network or api key')
        self._info('gateways started')

    def __connect_gateway(self, account_name: str, gateway_name: str, conf: Dict):
        if not account_name or not gateway_name or not conf:
            raise Exception('connect_gateway: config incorrect')
        gkey = self.gateway_key(account_name, gateway_name)
        if self.gateways.get(gkey, None) is not None:
            self._info('connect_gateway: gateway {} not empty, do nothing'.format(gkey))
            return 'gateway {} not empty, do nothing'.format(gkey)
        abpwd = os.getenv("ABPWD", "abquanT%go2moon!")
        cls = SUPPORTED_GATEWAY.get(gateway_name)
        if not cls:
            raise Exception('ExchangeOperation: No gateway class found in supported gateways')
        if 'encrypt_key' in conf and 'encrypt_secret' in conf:
            try:
                conf['key'] = decrypt(conf['encrypt_key'], abpwd)
                conf['secret'] = decrypt(conf['encrypt_secret'], abpwd)
                # conf.pop('encrypt_key')
                # conf.pop('encrypt_secret')
            except Exception as e:
                self._info(f'Error occurs when decrypting key and secret for gateway {gateway_name}')
                raise e
        else:
            raise Exception('ExchangeOperation: No encrypt key or secret specified')
        self._info(f'connect gateway start {gateway_name} for account {account_name}')
        gw = cls(self._event_dispatcher)
        gw.connect(conf)
        self.gateways[gkey] = gw
        time.sleep(10)
        self._info(f'connect gateway end {gateway_name} for account {account_name}')

    def _on_order(self, event):
        order: OrderData = event.data
        if not order.ab_orderid:
            return
        orig_order = self.orders.get(order.ab_orderid, None)
        self.orders.update({order.ab_orderid: order})
        if orig_order and not order.datetime and orig_order.datetime:
            order.datetime = orig_order.datetime
        for order_ in list(self.orders.values()):
            current = datetime.utcnow()
            if order_.datetime and (current - order_.datetime).total_seconds() > 600 \
                    and (order_.status == Status.REJECTED or order_.status == Status.ALLTRADED or order_.status == Status.CANCELLED):
                self.orders.pop(order_.ab_orderid)
            elif not order_.datetime :
                order_.datetime = datetime.utcnow()

    def _on_account(self, event):
        account: AccountData = event.data
        if account and (account.balance or account.frozen):
            self.key_is_valid = True

    def get_order(self, client_order_id) -> OrderData:
        if not client_order_id:
            return None
        return self.orders.get(client_order_id, None)

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

    @staticmethod
    def extract_key(gateway_key):
        if not gateway_key:
            return None, None
        items = gateway_key.split('.')
        if len(items) < 2:
            return None, None
        gateway_name = items[-1]
        account_name = gateway_key[: -1 - 1 * len(gateway_name)]
        return account_name, gateway_name

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
        if position.direction == Direction.NET:
            direction = Direction.LONG if position.volume < 0 else Direction.SHORT
        else:
            direction = Direction.LONG if position.direction == Direction.SHORT else Direction.SHORT
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
        gateway = self.gateways.get(self.gateway_key(account_name, gateway_name))
        if not gateway:
            raise Exception(
                f"Warning: cancel_order_list: no gateway [{account_name}.{gateway_name}] found for order, do nothing")
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
                         direction: Direction, offset: Offset, order_type: OrderType):
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

    def send_order_with_result(self, account_name, gateway_name, symbol: str,
                         price: float, volume: float,
                         direction: Direction, offset: Offset, order_type: OrderType):
        """
            发送订单，并返回交易所结果；等待结果超时，认为发送成功
            timeout：3s
        """
        order_ids = self.send_order(account_name, gateway_name, symbol, price, volume, direction, offset, order_type)
        for t in range(0, 60):
            time.sleep(0.05)
            order: OrderData = self.orders.get(order_ids, None)
            if not order or order.status == Status.SUBMITTING:
                continue
            elif order.status == Status.CANCELLED:
                self._info(f'order CANCELLED: {order.reference}')
                return OperationResult(ResultCode.CANCELLED, order_ids, 'order cancelled')
            elif order.status == Status.REJECTED:
                try:
                    jres = json.loads(order.reference)
                    if 'msg' in jres:
                        extra = jres.get('msg')
                    elif 'ret_msg' in jres:
                        extra = jres.get('ret_msg')
                    elif 'error' in jres:
                        extra = jres.get('error').get('message')
                    else:
                        extra = None
                    self._info(f'order REJECTED: {extra}')
                    return OperationResult(ResultCode.REJECTED, order_ids, extra)
                except:
                    self._info(f'error when seeking order.reference: {order.reference}')
                    continue
            else:
                self._info(order.status)
                return OperationResult(ResultCode.SUCCESS, order_ids, 'send order success')
        self._info(f'order not return from gateway in 3s, make it success')
        return OperationResult(ResultCode.SUCCESS, order_ids, f'order not return from gateway in 3s, make it success')

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

    def cancel_order(self, account_name, gateway_name, order: OrderData):
        """
            取消订单
        """
        # gateway_name = order.gateway_name
        gateway = self.gateways.get(self.gateway_key(account_name, gateway_name))
        req = order.create_cancel_request()
        gateway.cancel_order(req)

    def cancel_order_with_result_by_client_order_id(self, account_name, gateway_name, client_order_id):
        order = self.get_order(client_order_id)
        return self.cancel_order_with_result(account_name, gateway_name, order)

    def cancel_order_with_result(self, account_name, gateway_name, order: OrderData):
        """
            取消订单
        """
        if not order:
            return OperationResult(ResultCode.ERROR, None, 'order not exist')
        client_order_id = order.ab_orderid
        self.cancel_order(account_name, gateway_name, order)
        for t in range(0, 60):
            time.sleep(0.05)
            order: OrderData = self.orders.get(client_order_id, None)
            if order and order.status != Status.CANCELLED:
                continue
            else:
                return OperationResult(ResultCode.CANCELLED, client_order_id, 'order cancelled')
        return OperationResult(ResultCode.TIMEOUT, client_order_id, 'cancel order timeout')


class ResultCode(Enum):
    SUCCESS = 'SUCCESS'
    CANCELLED = 'CANCELLED'
    REJECTED = 'REJECTED'
    TIMEOUT = 'TIMEOUT'
    ERROR = 'ERROR'


@dataclass
class OperationResult:
    """
        交易所操作结果
    """
    code: ResultCode
    resid: str
    message: str


if __name__ == '__main__':
    _account_name = 'test'
    _gateway_name = 'BINANCEUBC'
    _config = {'operation': {
        'accounts': [{
            'name': _account_name,
            'gateways': _gateway_name,
            'encrypt_key': 'by40coj7CQfIre2Pq0wNDHyAx0ms1MPJ3jrRtf+PxF1qDOWhqunt6TCL2+PMGOcKBcShAdG18NDnMnqnteBl9Q==',
            'encrypt_secret': '+NnsuCW0OlDUmcfHktf8E/Z7xyq4jcwRrR6Uw6Eh/MSHRXkCuDlCuaOYRXPHngv3iudAwJUzgmKbntd94dXezQ==',
            'proxy_host': 'localhost',
            'proxy_port': 1087,
            "position_mode": ["One-way", "Hedge"][1],
            'is_prod': True
        }]
    }}
    exo = ExchangeOperation(_config)
    if True:
        for i in range(0,2):
            _ab_orderids = exo.send_order_with_result(_account_name, _gateway_name, 'BTCUSDT', 40000.0 + i, 0.001, Direction.LONG, Offset.OPEN, OrderType.LIMIT)
            print(_ab_orderids)
            _ab_orderids = exo.short(_account_name, _gateway_name, 'BTCUSDT', 50000.0 + i, 0.001, OrderType.LIMIT)
            print(_ab_orderids)
    else:
        _gateway = exo.gateways.get(exo.gateway_key(_account_name, _gateway_name))
        # clear position -------------------------------------------------
        _position_list = []
        _positions = _gateway.event_dispatcher.order_manager.positions
        for _, _pos in _positions.items():
            if _pos.volume:
                _position_list.append(_pos)
        while _position_list:   # 彻底清仓
            print('position remains')
            exo.clear_position_list(_account_name, _gateway_name, _position_list)
            _position_list.clear()
            time.sleep(10)
            _positions = _gateway.event_dispatcher.order_manager.positions
            for _, _pos in _positions.items():
                if _pos.volume:
                    _position_list.append(_pos)
        print('position cleared')
        # cancel order ----------------------------------------------------
        _order_list = []
        _orders = _gateway.event_dispatcher.order_manager.orders
        while _orders:  # 彻底撤销
            print('order remains')
            for _, _pos in _orders.items():
                _order_list.append(_pos)
            exo.cancel_order_list(_account_name, _gateway_name, _order_list)
            _order_list.clear()
            time.sleep(10)
            _orders = _gateway.event_dispatcher.order_manager.orders
        print('orders canceled')
