from typing import List, Dict
import time
import hmac
import hashlib
import json
from datetime import datetime
from requests.exceptions import SSLError
import base64
import pytz

from . import DIRECTION_DYDX2AB, DIRECTION_AB2DYDX, WEBSOCKET_HOST, TESTNET_WEBSOCKET_HOST, REST_HOST, TESTNET_REST_HOST, INTERVAL_AB2DYDX, ORDERTYPE_AB2DYDX, STATUS_DYDX2AB,ORDERTYPE_DYDX2AB, symbol_contract_map, Security
from ..accessor import Request, RestfulAccessor
from ..basegateway import Gateway
from abquant.trader.msg import BarData, OrderData
from abquant.trader.common import Direction, Exchange, Offset, OrderType, Product, Status
from abquant.trader.object import AccountData, CancelRequest, ContractData, HistoryRequest, OrderRequest, PositionData
from dydx_util import *


# 账户信息全局缓存字典
api_key_credentials_map: Dict[str, str] = {}

# UTC时区
UTC_TZ = pytz.utc

class DydxAccessor(RestfulAccessor):

    def __init__(self, gateway: Gateway):
        super(DydxAccessor, self).__init__(gateway)

    def sign(self, request: Request) -> Request:
        """生成dYdX签名"""
        security = request.data["security"]
        now_iso_string = generate_now_iso()
        if security == Security.PUBLIC:
            request.data = None
            return request

        else:
            request.data.pop("security")
            signature: str = sign(
                request_path=request.path,
                method=request.method,
                iso_timestamp=now_iso_string,
                data=request.data
            )
            request.data = json.dumps(request.data)

        headers = {
            "DYDX-SIGNATURE": signature,
            "DYDX-API-KEY": api_key_credentials_map["key"],
            "DYDX-TIMESTAMP": now_iso_string,
            "DYDX-PASSPHRASE": api_key_credentials_map["passphrase"],
            "Accept": 'application/json',
            "Content-Type": 'application/json'
        }
        request.headers = headers

        return request 

    def connect(
        self,
        server: str,
        proxy_host: str,
        proxy_port: int,
        limitFee: float
    ) -> None:
        """连接REST服务器"""
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host
        self.server = server
        self.limitFee = limitFee

        if self.server == "REAL":
            self.init(REST_HOST, proxy_host, proxy_port)
        else:
            self.init(TESTNET_REST_HOST, proxy_host, proxy_port)

        self.start()
        self.query_contract()

        self.gateway.write_log("REST API启动成功")

    def query_contract(self) -> None:
        """查询合约信息"""
        data: dict = {
            "security": Security.PUBLIC
        }

        self.add_request(
            method="GET",
            path="/v3/markets",
            callback=self.on_query_contract,
            data=data
        )

    def query_account(self) -> None:
        """查询资金"""
        data: dict = {
            "security": Security.PRIVATE
        }

        self.add_request(
            method="GET",
            path=f"/v3/accounts/{self.gateway.id}",
            callback=self.on_query_account,
            data=data
        )

    def new_orderid(self) -> str:
        """生成本地委托号"""
        prefix: str = datetime.now().strftime("%Y%m%d%H%M%S")

        self.order_count += 1
        suffix: str = str(self.order_count).rjust(8, "0")

        orderid: str = prefix + suffix
        return orderid

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        # 生成本地委托号
        orderid: str = self.new_orderid()

        # 推送提交中事件
        order: OrderData = req.create_order_data(
            orderid,
            self.gateway_name
        )
        self.gateway.on_order(order)

        expiration_epoch_seconds: int = int(time.time() + 86400)

        hash_namber: int = generate_hash_number(
            server=self.server,
            position_id=self.gateway.posid,
            client_id=orderid,
            market=req.symbol,
            side=DIRECTION_AB2DYDX[req.direction],
            human_size=str(req.volume),
            human_price=str(req.price),
            limit_fee=str(self.limitFee),
            expiration_epoch_seconds=expiration_epoch_seconds
        )

        signature: str = order_to_sign(hash_namber, api_key_credentials_map["stark_private_key"])

        # 生成委托请求
        data: dict = {
            "security": Security.PRIVATE,
            "market": req.symbol,
            "side": DIRECTION_AB2DYDX[req.direction],
            "type": ORDERTYPE_AB2DYDX[req.type],
            "timeInForce": "GTT",
            "size": str(req.volume),
            "price": str(req.price),
            "limitFee": str(self.limitFee),
            "expiration": epoch_seconds_to_iso(expiration_epoch_seconds),
            "postOnly": False,
            "clientId": orderid,
            "signature": signature
        }

        self.add_request(
            method="POST",
            path="/v3/orders",
            callback=self.on_send_order,
            data=data,
            extra=order,
            on_error=self.on_send_order_error,
            on_failed=self.on_send_order_failed
        )

        return order.vt_orderid

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        order_no: str = self.gateway.local_sys_map.get(req.orderid, "")
        if not order_no:
            self.gateway.write_log(f"撤单失败，找不到{req.orderid}对应的系统委托号")
            return

        data: dict = {
            "security": Security.PRIVATE
        }

        order: OrderData = self.gateway.get_order(req.orderid)

        self.add_request(
            method="DELETE",
            path=f"/v3/orders/{order_no}",
            callback=self.on_cancel_order,
            data=data,
            on_failed=self.on_cancel_failed,
            extra=order
        )

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        history: List[BarData] = []
        data: dict = {
            "security": Security.PUBLIC
        }

        params: dict = {
            "resolution": INTERVAL_AB2DYDX[req.interval]
        }

        resp = self.request(
            method="GET",
            path=f"/v3/candles/{req.symbol}",
            data=data,
            params=params
        )

        if resp.status_code // 100 != 2:
            msg: str = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
            self.gateway.write_log(msg)

        else:
            data: dict = resp.json()
            if not data:
                self.gateway.write_log("获取历史数据为空")

            for d in data["candles"]:

                bar: BarData = BarData(
                    symbol=req.symbol,
                    exchange=req.exchange,
                    datetime=generate_datetime(d["startedAt"]),
                    interval=req.interval,
                    volume=float(d["baseTokenVolume"]),
                    open_price=float(d["open"]),
                    high_price=float(d["high"]),
                    low_price=float(d["low"]),
                    close_price=float(d["close"]),
                    turnover=float(d["usdVolume"]),
                    open_interest=float(d["startingOpenInterest"]),
                    gateway_name=self.gateway_name
                )
                history.append(bar)

            begin: datetime = history[-1].datetime
            end: datetime = history[0].datetime

            msg: str = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
            self.gateway.write_log(msg)

        return history

    def on_query_contract(self, data: dict, request: Request) -> None:
        """合约信息查询回报"""
        for d in data["markets"]:
            contract: ContractData = ContractData(
                symbol=d,
                exchange=Exchange.DYDX,
                name=d,
                pricetick=data["markets"][d]["tickSize"],
                size=data["markets"][d]["stepSize"],
                min_volume=data["markets"][d]["minOrderSize"],
                product=Product.FUTURES,
                net_position=True,
                history_data=True,
                gateway_name=self.gateway_name
            )
            self.gateway.on_contract(contract)

            symbol_contract_map[contract.symbol] = contract

        self.gateway.write_log("合约信息查询成功")

    def on_query_account(self, data: dict, request: Request) -> None:
        """资金查询回报"""
        d: dict = data["account"]
        balance: float = float(d["equity"])
        available: float = float(d["freeCollateral"])
        account: AccountData = AccountData(
            accountid=d["id"],
            balance=balance,
            frozen=balance - available,
            gateway_name=self.gateway_name
        )

        self.gateway.on_account(account)

        for keys in d["openPositions"]:
            position: PositionData = PositionData(
                symbol=keys,
                exchange=Exchange.DYDX,
                direction=Direction.NET,
                volume=float(d["openPositions"][keys]["size"]),
                price=float(d["openPositions"][keys]["entryPrice"]),
                pnl=float(d["openPositions"][keys]["unrealizedPnl"]),
                gateway_name=self.gateway_name
            )
            if d["openPositions"][keys]["size"] == "SHORT":
                position.volume = -position.volume
            self.gateway.on_position(position)

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

        if not issubclass(exception_type, (ConnectionError, SSLError)):
            self.on_error(exception_type, exception_value, tb, request)

    def on_send_order_failed(self, status_code: str, request: Request) -> None:
        """委托下单失败服务器报错回报"""
        order: OrderData = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        msg: str = f"委托失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg)

    def on_cancel_order(self, data: dict, request: Request) -> None:
        """委托撤单回报"""
        pass

    def on_cancel_failed(self, status_code: str, request: Request) -> None:
        """撤单回报函数报错回报"""
        if request.extra:
            order: OrderData = request.extra
            order.status = Status.REJECTED
            self.gateway.on_order(order)

        msg: str = f"撤单失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg)

def generate_datetime(timestamp: str) -> datetime:
    """生成时间"""
    dt: datetime = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
    dt: datetime = UTC_TZ.localize(dt)
    return dt


def generate_now_iso() -> str:
    """生成ISO时间"""
    return datetime.utcnow().strftime(
        '%Y-%m-%dT%H:%M:%S.%f',
    )[:-3] + 'Z'


def epoch_seconds_to_iso(epoch: float) -> str:
    """时间格式转换"""
    return datetime.utcfromtimestamp(epoch).strftime(
        '%Y-%m-%dT%H:%M:%S.%f',
    )[:-3] + 'Z'


def sign(
    request_path: str,
    method: str,
    iso_timestamp: str,
    data: dict,
) -> str:
    """生成签名"""
    body: str = ""
    if data:
        body = json.dumps(data, separators=(',', ':'))

    message_string = "".join([
        iso_timestamp,
        method,
        request_path,
        body
    ])

    hashed = hmac.new(
        base64.urlsafe_b64decode(
            (api_key_credentials_map["secret"]).encode('utf-8'),
        ),
        msg=message_string.encode('utf-8'),
        digestmod=hashlib.sha256,
    )
    return base64.urlsafe_b64encode(hashed.digest()).decode()
