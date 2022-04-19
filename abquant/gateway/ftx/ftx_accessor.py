import json
from typing import List
from threading import Lock
import time
import hmac
from datetime import datetime, timedelta
import uuid

from . import DIRECTION_AB2FTX, DIRECTION_FTX2AB, LIMIT_AB2FTX, ORDERTYPE_AB2FTX, ORDERTYPE_FTX2AB, PRODUCTTYPE_FTX2AB, REST_HOST, INTERVAL_AB2FTX, INTERVAL_FTX2AB , Security, symbol_contract_map, change_datetime, generate_datetime
from ..accessor import Request, RestfulAccessor
from ..basegateway import Gateway
from abquant.trader.msg import BarData, OrderData
from abquant.trader.common import  Exchange, Status
from abquant.trader.object import AccountData, CancelRequest, ContractData, HistoryRequest, OrderRequest, PositionData

class FtxAccessor(RestfulAccessor):
    """FTX的REST API"""
    ORDER_PREFIX = str(hex(uuid.getnode()))

    def __init__(self, gateway: Gateway) -> None:
        """"""
        super(FtxAccessor, self).__init__(gateway)

        self.gateway: Gateway = gateway

        # 保存用户登陆信息
        self.key: str = ""
        self.secret: str = ""

        # 确保生成的orderid不发生冲突
        self.order_count: int = 1_000_000
        self.order_count_lock: Lock = Lock()
        self.connect_time: int = 0

    def sign(self, request: Request) -> Request:
        """签名"""
        security = request.data["security"]
        request.data.pop("security")

        if security == Security.NONE:
            request.data = None
            return request

        if security == Security.SIGNED:
            timestamp = int(time.time() * 1000)
            signature_payload = f'{timestamp}{request.method}{request.path}'

            if request.data:
                request.data = json.dumps(request.data)
                signature_payload += request.data
            signature_payload = signature_payload.encode()
            signature = hmac.new(self.secret, signature_payload, 'sha256').hexdigest()

            if request.headers is None:
                request.headers = {'Content-Type': 'application/json'}

            request.headers['FTX-KEY'] = self.key
            request.headers['FTX-SIGN'] = signature
            request.headers['FTX-TS'] = str(timestamp)

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

        self.init(REST_HOST, self.proxy_host, self.proxy_port)
        self.start()

        self.gateway.write_log("REST API启动成功")

        self.query_account()
        self.query_position()
        self.query_order()
        self.query_contract()

    def query_account(self) -> None:
        """查询资金"""
        data: dict = {"security": Security.SIGNED}

        path: str = "/api/wallet/balances"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_account,
            data=data
        )

    def query_position(self) -> None:
        """查询持仓"""
        data: dict = {"security": Security.SIGNED}

        path: str = "/api/positions"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_position,
            data=data
        )

    def query_order(self) -> None:
        """查询未成交委托"""
        data: dict = {"security": Security.SIGNED}

        path: str = "/api/orders"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_order,
            data=data
        )

    def query_contract(self) -> None:
        """查询合约信息"""
        data: dict = {"security": Security.NONE}

        path: str = "/api/markets"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_contract,
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
        orderid = self.ORDER_PREFIX + str(self.connect_time + self._new_order_id())
        
        # 推送提交中事件
        order: OrderData = req.create_order_data(
            orderid,
            self.gateway_name
        )

        data: dict = {
            "market": req.symbol.upper(),
            "side": DIRECTION_AB2FTX[req.direction],
            "price": str(req.price),
            "size": str(req.volume),
            "type": ORDERTYPE_AB2FTX[req.type],
            "reduceOnly": False,
            "ioc": False,
            "postOnly": False,
            "clientId": orderid,
            "rejectOnPriceBand": False,
            "security": Security.SIGNED
        }

        self.add_request(
            method="POST",
            path="/api/orders",
            callback=self.on_send_order,
            data=data,
            extra=order,
            on_error=self.on_send_order_error,
            on_failed=self.on_send_order_failed
        )

        self.gateway.on_order(order)
        return order.ab_orderid

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        data: dict = {"security": Security.SIGNED}

        path: str = "/api/orders/by_client_id/" + req.orderid

        order: OrderData = self.gateway.get_order(req.orderid)

        self.add_request(
            method="DELETE",
            path=path,
            callback=self.on_cancel_order,
            data=data,
            on_failed=self.on_cancel_failed,
            extra=order
        )

    def on_query_account(self, data: dict, request: Request) -> None:
        """资金查询回报"""
        for asset in data["result"]:
            account: AccountData = AccountData(
                accountid=asset["coin"],
                balance=asset["total"],
                gateway_name=self.gateway_name
            )
            account.available = asset["free"]
            account.frozen = account.balance - account.available

            if account.balance:
                self.gateway.on_account(account)

        self.gateway.write_log("账户资金查询成功")

    def on_query_position(self, data: dict, request: Request) -> None:
        """持仓查询回报"""
        for d in data["result"]:
            position: PositionData = PositionData(
                symbol=d["future"],
                exchange=Exchange.FTX,
                direction=DIRECTION_FTX2AB["net"],
                volume=d["netSize"],
                price=0,
                pnl=d["unrealizedPnl"] + d["realizedPnl"],
                gateway_name=self.gateway_name,
            )

            self.gateway.on_position(position)

        self.gateway.write_log("持仓信息查询成功")

    def on_query_order(self, data: dict, request: Request) -> None:
        """未成交委托查询回报"""
        for d in data["result"]:
            # 先判断订单状态
            current_status = d["status"]
            size = d["size"]
            filled_size = d["filledSize"]
            remaining_size = d["remainingSize"]
            if current_status == "new":
                status = Status.NOTTRADED
            elif (current_status == "open") & (filled_size == 0):
                status = Status.NOTTRADED
            elif (current_status == "open") & (size != filled_size):
                status = Status.PARTTRADED
            elif (current_status == "closed") & ((size != filled_size)):
                status = Status.CANCELLED
            elif (remaining_size == 0) & (size == filled_size):
                status = Status.ALLTRADED
            else:
                status = "other status"

            order: OrderData = OrderData(
                orderid=d["clientId"],
                symbol=d["market"],
                exchange=Exchange.FTX,
                price=d["price"],
                volume=d["size"],
                type=ORDERTYPE_FTX2AB[d["type"]],
                direction=DIRECTION_FTX2AB[d["side"]],
                traded=d["filledSize"],
                status=status,
                datetime=change_datetime(d["createdAt"]),
                gateway_name=self.gateway_name,
            )
            self.gateway.on_order(order)

        self.gateway.write_log("委托信息查询成功")

    def on_query_contract(self, data: dict, request: Request):
        """合约信息查询回报"""
        for d in data["result"]:
            contract: ContractData = ContractData(
                symbol=d["name"],
                exchange=Exchange.FTX,
                name=d["name"],
                pricetick=d["priceIncrement"],
                size=1,
                min_volume=d["sizeIncrement"],
                product=PRODUCTTYPE_FTX2AB[d["type"]],
                net_position=True,
                history_data=True,
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
        history: List[BarData] = []
        limit: int = LIMIT_AB2FTX[req.interval]

        start: int = int(datetime.timestamp(req.start))
        end: int = int(datetime.timestamp(req.end))

        tmp_start = max(start, end - INTERVAL_AB2FTX[req.interval] * limit)

        buf: List[BarData] = None

        while True:
            params = {
                "resolution": INTERVAL_AB2FTX[req.interval],
                "start_time": tmp_start,
                "end_time": end
            }

            path = f"/api/markets/{req.symbol}/candles?"

            resp = self.request(
                "GET",
                path,
                data={"security": Security.NONE},
                params=params
            )

            # 如果请求失败则终止循环
            if resp.status_code // 100 != 2:
                msg: str = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg)
                break
            else:
                data: dict = resp.json()
                # 整个时间段内都未有数据，终止循环
                if (not data["result"]) and (buf is None):
                    stop_time = datetime.utcfromtimestamp(tmp_start)
                    msg: str = f"获取历史数据为空，开始时间：{stop_time}"
                    self.gateway.write_log(msg)
                    break
                # 剩下的时间端内不再有数据，终止循环
                elif (not data["result"]) and (buf is not None):
                    msg: str = "获取历史数据完成"
                    self.gateway.write_log(msg)
                    break

                buf: List[BarData] = []

                for his_data in data["result"]:
                    bar = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=datetime.fromtimestamp(his_data["time"] / 1000),
                        interval=req.interval,
                        volume=his_data["volume"],
                        open_price=his_data["open"],
                        high_price=his_data["high"],
                        low_price=his_data["low"],
                        close_price=his_data["close"],
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)

                begin: datetime = buf[0].datetime
                end: datetime = buf[-1].datetime

                buf = list(reversed(buf))
                history.extend(buf)

                msg: str = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # 最后一段查询结束后终止
                if tmp_start == start:
                    msg: str = "获取历史数据完成"
                    self.gateway.write_log(msg)
                    break

                # 更新下一个时间段
                end = tmp_start
                tmp_start = max(start, end - INTERVAL_AB2FTX[req.interval] * limit)

        history = list(reversed(history))
        return history