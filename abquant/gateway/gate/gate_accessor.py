import json
from typing import List
from threading import Lock
import time
import hmac
from datetime import datetime, timedelta
import uuid
import hashlib
from urllib.parse import urlparse

from . import END_POINT, symbol_contract_map
from ..accessor import Request, RestfulAccessor
from ..basegateway import Gateway
from abquant.trader.msg import BarData, OrderData
from abquant.trader.common import Exchange, Status, OrderType, Product
from abquant.trader.object import AccountData, CancelRequest, ContractData, HistoryRequest, OrderRequest, PositionData

class GateAccessor(RestfulAccessor):
    """GATE的REST API"""
    ORDER_PREFIX = str(hex(uuid.getnode()))

    def __init__(self, gateway: Gateway) -> None:
        """"""
        super(GateAccessor, self).__init__(gateway)

        self.gateway: Gateway = gateway

        # 保存用户登陆信息
        self.key: str = ""
        self.secret: str = ""

        # 确保生成的orderid不发生冲突
        self.order_count: int = 1_000_000
        self.order_count_lock: Lock = Lock()
        self.connect_time: int = 0

        self._without_content_body_method = ['GET', 'DELETE', 'HEAD']

    def sign(self, request: Request) -> Request:
        """签名"""
        common_headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        method = request.method
        url = END_POINT+request.path
        request_headers = {} if request.headers is None else request.headers
        query_string = None
        if method in self._without_content_body_method:
            if '?' in url:
                split = url.split("?")
                query_string = split[1]
        t = time.time()
        m = hashlib.sha512()
        body = request.data
        if body is not None:
            m.update(body)
        hashed_payload = m.hexdigest()
        s = '%s\n%s\n%s\n%s\n%s' % (method, urlparse(url).path, query_string or "", hashed_payload, t)
        sign = hmac.new(self.secret, s.encode('utf-8'), hashlib.sha512).hexdigest()
        signature = {'KEY': self.key, 'Timestamp': str(t), 'SIGN': sign}
        signature.update(common_headers)
        request_headers.update(signature)
        request.headers = request_headers
        return request

    def connect(
        self,
        key: str,
        secret: str,
        proxy_host: str,
        proxy_port: int
    ) -> None:
        """"""
        self.key = key
        self.secret = secret.encode()
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        self.init(END_POINT, self.proxy_host, self.proxy_port)
        self.start()

        self.gateway.write_log("REST API启动成功")

        # self.query_account()
        # self.query_order()
        self.query_contract()

    def query_account(self) -> None:
        """查询资金"""
        path: str = "/spot/accounts"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_account,
        )

    def query_position(self) -> None:
        """查询持仓"""

    def query_order(self) -> None:
        """查询未成交委托"""

        path: str = "/spot/open_orders"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_order,
        )

    def query_contract(self) -> None:
        """查询合约信息"""
        path: str = "/spot/currency_pairs"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_contract,
        )


    def _new_order_id(self) -> int:
        """生成本地委托号"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        orderid = self.ORDER_PREFIX + str(self.connect_time + self._new_order_id())
        return orderid

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""


    def on_query_account(self, data: dict, request: Request) -> None:
        """资金查询回报"""

        for asset in data:
            account: AccountData = AccountData(
                accountid=asset["currency"],
                balance=float(asset["available"]),
                frozen=float(asset["locked"]),
                gateway_name=self.gateway_name
            )
            account.available = float(asset["available"])
            account.balance = account.available + account.frozen

            if account.balance:
                self.gateway.on_account(account)

        self.gateway.write_log("账户资金查询成功")

    def on_query_position(self, data: dict, request: Request) -> None:
        """持仓查询回报"""
        self.gateway.write_log("持仓信息查询成功")

    def on_query_order(self, data: dict, request: Request) -> None:
        """未成交委托查询回报"""

        for d in data:
            # 先判断订单状态
            current_status = d["status"]
            left = float(d["left"])
            filled_size = float(d["amount"])
            if current_status == "open":
                status = Status.NOTTRADED
            elif (current_status == "open") & (filled_size == 0):
                status = Status.NOTTRADED
            elif (current_status == "open") & (left != 0):
                status = Status.PARTTRADED
            elif (current_status == "cancelled") & (filled_size > 0):
                status = Status.PARTTRADED
            elif (current_status == "cancelled") :
                status = Status.CANCELLED
            elif (current_status == 'closed') & (left == 0):
                status = Status.ALLTRADED
            else:
                status = "other status"

            order: OrderData = OrderData(
                orderid=d["text"],
                symbol=d["currency_pair"],
                exchange=Exchange.GATE,
                price=d["price"],
                volume=d["amount"],
                type=OrderType.LIMIT,
                direction=d["side"],
                traded=d["amount"],
                status=status,
                datetime=d["update_time"],
                gateway_name=self.gateway_name,
            )
            self.gateway.on_order(order)

        self.gateway.write_log("委托信息查询成功")

    def on_query_contract(self, data: dict, request: Request):
        """合约信息查询回报"""
        data = list(filter(lambda x: x['trade_status'] == 'tradable', data))
        for d in data:
            symbol = d["id"].lower().replace('_','')
            contract: ContractData = ContractData(
                symbol=symbol,
                exchange=Exchange.GATEIO,
                name=d["id"],
                pricetick=d["precision"],
                size=1,
                product=Product.SPOT,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_contract(contract)

            symbol_contract_map[contract.symbol] = contract

        self.gateway.write_log("合约信息查询成功")

    def on_send_order(self, data: dict, request: Request) -> None:
        """委托下单回报"""
        pass

    def on_send_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ) -> None:
        """委托下单回报函数报错回报"""
        order: OrderData = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)

    def on_send_order_failed(self, status_code: str, request: Request) -> None:
        """委托下单失败服务器报错回报"""
        order: OrderData = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        msg: str = f"委托失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg)

    def on_cancel_order(self, status_code: str, request: Request) -> None:
        """委托撤单回报"""
        pass

    def on_cancel_failed(self, status_code: str, request: Request):
        """撤单回报函数报错回报"""
        if request.extra:
            order = request.extra
            order.status = Status.REJECTED
            self.gateway.on_order(order)

        msg = f"撤单失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg)

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
