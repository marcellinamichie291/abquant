from datetime import datetime
from typing import List
import json
import time
from requests.exceptions import SSLError
import uuid
from threading import Lock

from ..accessor import Request
from ...trader.msg import BarData
from ...trader.object import (
    OrderData,
    AccountData,
    CancelRequest,
    HistoryRequest,
    OrderRequest,
    ContractData,
    PositionData,
    HistoryRequest,
    Product,
    Status,
    Direction
)
from ...trader.common import Exchange, OrderType
from . import (
    DIRECTION_AB2DYDX,
    DIRECTION_DYDX2AB,
    ORDERTYPE_DYDX2AB,
    REST_HOST,
    STATUS_DYDX2AB,
    TESTNET_REST_HOST,
    INTERVAL_AB2DYDX,
    ORDERTYPE_AB2DYDX,
    TIMEDELTA_MAP,
    symbol_contract_map,
    Security
)
from ..basegateway import Gateway
from ..accessor import Request, RestfulAccessor
from .dydx_util import (
    generate_datetime,
    api_key_credentials_map,
    generate_datetime_iso,
    sign,
    generate_now_iso,
    generate_hash_number,
    order_to_sign,
    epoch_seconds_to_iso
)
from abquant.trader.utility import round_to


class DydxAccessor(RestfulAccessor):
    """
    dydx rest接口
    签名
    下单、撤单、查询交易信息
    """
    ORDER_PREFIX = str(hex(uuid.getnode()))

    def __init__(self, gateway: Gateway):
        super(DydxAccessor, self).__init__(gateway)
        self.gateway: Gateway = gateway
        self.gateway.set_gateway_name(gateway.gateway_name)
        self.order_count: int = 0
        self.position_id = ""
        self.connect_time = 0
        self.order_count: int = 1_000_000
        self.order_count_lock: Lock = Lock()

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
            limitFee: float) -> None:
        """连接REST服务器"""
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host
        self.server = server
        self.limitFee = limitFee

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        if self.server == "REAL":
            self.init(REST_HOST, proxy_host, proxy_port)
        else:
            self.init(TESTNET_REST_HOST, proxy_host, proxy_port)

        self.start()
        self.query_contract()
        self.query_account()
        # self.gateway.init_query()

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

    def _new_order_id(self) -> int:
        """生成本地委托号"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        # 生成本地委托号
        orderid = self.ORDER_PREFIX + \
            str(self.connect_time + self._new_order_id())

        # 推送提交中事件
        order: OrderData = req.create_order_data(
            orderid,
            self.gateway_name
        )
        self.gateway.on_order(order)

        expiration_epoch_seconds: int = int(time.time() + 86400)
        
        order_type, timeInForce = ORDERTYPE_AB2DYDX[req.type]
        post_only = True if req.type == OrderType.POSTONLYLIMIT else False
        contract = symbol_contract_map.get(req.symbol)
        if contract:
            price = round_to(req.price, contract.pricetick)
            volume = round_to(req.volume, contract.step_size)

        hash_namber: int = generate_hash_number(
            server=self.server,
            position_id=self.position_id,
            client_id=orderid,
            market=req.symbol,
            side=DIRECTION_AB2DYDX[req.direction],
            human_size=str(volume),
            human_price=str(price),
            limit_fee=str(self.limitFee),
            expiration_epoch_seconds=expiration_epoch_seconds
        )

        signature: str = order_to_sign(
            hash_namber, api_key_credentials_map["stark_private_key"])

        # 生成委托请求
        data: dict = {
            "security": Security.PRIVATE,
            "market": req.symbol,
            "side": DIRECTION_AB2DYDX[req.direction],
            "type": order_type,
            "timeInForce": timeInForce,
            "size": str(volume),
            "price": str(price),
            "limitFee": str(self.limitFee),
            "expiration": epoch_seconds_to_iso(expiration_epoch_seconds),
            "postOnly": post_only,
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

        return order.ab_orderid

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

    def query_canceled_orders(self) -> None:
        """查询已经撤销订单"""
        data: dict = {
            "security": Security.PRIVATE,
            "status": ["CANCELED"],
            "tpye": ["LIMIT"],
            "limit": 100,
            
        }

        self.add_request(
            method="GET",
            path=f"/v3/orders",
            callback=self.on_query_canceled_orders,
            data=data
        )

    def on_query_canceled_orders(self, data: dict, request: Request) -> None :
        """查询未成交订单回报"""
        # print("------on_query_orders-----", data)
        for order_data in data["orders"]:
            # 绑定本地和系统委托号映射
            self.gateway.local_sys_map[order_data["clientId"]] = order_data["id"]
            self.gateway.sys_local_map[order_data["id"]] = order_data["clientId"]
            order: OrderData = OrderData(
                symbol=order_data["market"],
                exchange=Exchange.DYDX,
                orderid=order_data["clientId"],
                type=ORDERTYPE_DYDX2AB[order_data["type"]],
                direction=DIRECTION_DYDX2AB[order_data["side"]],
                # offset=Offset.NONE,
                price=float(order_data["price"]),
                volume=float(order_data["size"]),
                traded=float(order_data["size"]) - \
                float(order_data["remainingSize"]),
                status=STATUS_DYDX2AB.get(
                    order_data["status"], Status.SUBMITTING),
                datetime=generate_datetime(order_data["createdAt"]),
                gateway_name=self.gateway_name
            )
            if 0 < order.traded < order.volume:
                order.status = Status.PARTTRADED
            self.gateway.on_order(order)
    
    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        limit = 100
        history: List[BarData] = []
        data: dict = {
            "security": Security.PUBLIC
        }

        params: dict = {
            "resolution": INTERVAL_AB2DYDX[req.interval],
            "limit": limit
        }

        end_dt = req.end if req.end else datetime.now()
        start_dt = req.start if req.start else end_dt - limit * TIMEDELTA_MAP[req.interval]

        while 1:
            
            buf = []
            if end_dt:
                params["toISO"] = generate_datetime_iso(end_dt)

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
                bars: dict = resp.json()
                if not bars:
                    self.gateway.write_log("获取历史数据为空")

                for d in bars["candles"]:

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
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)
                history.extend(buf)
                
                begin: datetime = buf[-1].datetime
                end: datetime = buf[0].datetime

                msg: str = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)
                
                if len(bars["candles"]) < limit:
                    break
                if begin < start_dt:
                    break
                end_dt = bar.datetime
                

        return list(reversed(history))

    def on_query_contract(self, data: dict, request: Request) -> None:  # ok
        """合约信息查询回报"""
        for d in data["markets"]:
            contract: ContractData = ContractData(
                symbol=d,
                exchange=Exchange.DYDX,
                name=d,
                pricetick=data["markets"][d]["tickSize"],
                size=1,
                step_size=data["markets"][d]["stepSize"],
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
        # dydx 有时候返回accounts 有时候返回account
        d: dict = data["accounts"][0] if "accounts" in data else data["account"]
        self.position_id = d["positionId"]
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
        """撤单成功回报"""
        pass

    def on_cancel_failed(self, status_code: str, request: Request) -> None:
        """撤单回报函数报错回报"""
        if request.extra:
            order: OrderData = request.extra
            order.status = Status.REJECTED
            self.gateway.on_order(order)

        msg: str = f"撤单失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg)

    def testnet_token(self) -> None:
        """测试网络获取测试币"""
        data: dict = {
            "security": Security.PRIVATE
        }

        self.add_request(
            method="POST",
            path=f"/v3/testnet/tokens",
            callback=self.gateway.write_log,
            data=data
        )
