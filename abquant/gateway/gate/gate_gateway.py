#! /usr/bin/env/Python
# -*- coding:utf-8 -*-
"""
@author: baijy
@time: 2022/5/11 9:29 AM
@desc:
"""
from copy import copy
from typing import Dict, Iterable, List
from abquant.trader.msg import BarData, OrderData
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeRequest
from .gate_accessor import GateAccessor
from .gate_listener import GateWebsocketListener
from abquant.event import EventDispatcher
from abquant.trader.common import Exchange
from abquant.gateway.basegateway import Gateway


class GateGateway(Gateway):
    default_setting = {
        "key": "",
        "secret": "",
        "proxy_host": "",
        "proxy_port": 0
    }
    exchanges: Exchange = [Exchange.GATEIO]

    def __init__(self, event_dispatcher: EventDispatcher, gateway_name: str = "GATEIO") -> None:
        """构造函数"""
        super().__init__(event_dispatcher, gateway_name)
        self.set_gateway_name(gateway_name)
        self.listener = GateWebsocketListener(self)
        self.accessor = GateAccessor(self)

        self.orders: Dict[str, OrderData] = {}
        self.order_id: Dict[str, str] = {}

    def connect(self, setting: dict) -> None:
        """连接交易接口"""
        key: str = setting["key"]
        secret: str = setting["secret"]
        proxy_host: str = setting["proxy_host"]
        proxy_port: int = setting["proxy_port"]

        self.accessor.connect(key, secret, proxy_host, proxy_port)
        self.listener.connect(key, secret, proxy_host, proxy_port)

        self.on_gateway(self)

    def start(self):
        self.listener.start()

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.listener.subscribe(req)

    def send_order(self, req: OrderRequest) -> None:
        """委托下单"""
        raise NotImplementedError(
            "do not use this method.")

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        raise NotImplementedError(
            "do not use this method.")

    def cancel_orders(self, reqs: Iterable[CancelRequest]) -> None:
        raise NotImplementedError(
            "do not use this method.")

    def query_account(self) -> None:
        """查询资金"""
        self.accessor.query_account()

    def query_position(self) -> None:
        """查询持仓"""
        raise NotImplementedError(
            "do not use this method.")

    def query_orders(self) -> None:
        """查询未成交委托"""
        raise NotImplementedError(
            "do not use this method.")

    def on_order(self, order: OrderData) -> None:
        """推送委托数据"""
        self.orders[order.orderid] = copy(order)
        raise NotImplementedError(
            "do not use this method.")

    def get_order(self, orderid: str) -> OrderData:
        """查询委托数据"""
        raise NotImplementedError(
            "do not use this method.")

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        raise NotImplementedError(
            "do not use this method.")

    def close(self) -> None:
        """关闭连接"""
        self.accessor.stop()
        self.listener.stop()


