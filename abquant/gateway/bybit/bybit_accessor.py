from datetime import datetime
from threading import Lock
from typing import List
import uuid
from abquant.trader.common import Direction, Exchange, Offset, Product, Status
from abquant.trader.msg import BarData, OrderData

from abquant.trader.object import AccountData, CancelRequest, ContractData, HistoryRequest, OrderRequest, PositionData

from ..accessor import Request, RestfulAccessor
from ..basegateway import Gateway
from .bybit_util import generate_timestamp, generate_datetime_2, generate_datetime, sign
from . import (
    DIRECTION_AB2BYBIT,
    DIRECTION_BYBIT2AB,
    INTERVAL_AB2BYBIT,
    ORDER_TYPE_AB2BYBIT,
    ORDER_TYPE_BYBIT2AB,
    REST_HOST,
    STATUS_BYBIT2AB,
    TESTNET_REST_HOST,
    TIMEDELTA_MAP,
    ubc_symbol_contract_map,
    bbc_symbol_contract_map,
    future_symbol_contract_map,
    local_orderids
)


def build_raw_data(data, gateway_name: str, data_type):
    return {
        'type': 'data_restfull',
        'gateway_name': gateway_name,
        'data_type': data_type,
        'payload': data
    }


class BybitUBCAccessor(RestfulAccessor):
    """U本位合约的REST接口"""
    ORDER_PREFIX = str(hex(uuid.getnode()))

    def __init__(self, gateway: Gateway):
        """构造函数"""
        super(BybitUBCAccessor, self).__init__(gateway)

        self.gateway: Gateway = gateway

        self.key: str = ""
        self.secret: bytes = b""
        self.position_mode: str = ""

        self.connect_time: int = 0

        self.order_count: int = 1_000_000
        self.order_count_lock: Lock = Lock()

    def sign(self, request: Request) -> Request:
        """生成签名"""
        request.headers = {"Referer": "abquant"}

        if request.method == "GET":
            api_params: dict = request.params
            if api_params is None:
                api_params = request.params = {}
        else:
            api_params: dict = request.data
            if api_params is None:
                api_params = request.data = {}

        api_params["api_key"] = self.key
        api_params["recv_window"] = 30 * 1000
        api_params["timestamp"] = generate_timestamp(-5)

        data2sign = "&".join([f"{k}={v}" for k, v in sorted(api_params.items())])
        signature: str = sign(self.secret, data2sign.encode())
        api_params["sign"] = signature

        return request

    def connect(
            self,
            key: str,
            secret: str,
            position_mode: str,
            server: str,
            proxy_host: str,
            proxy_port: int,
    ) -> None:
        """连接服务器"""
        self.key = key
        self.secret = secret.encode()
        self.position_mode = position_mode

        if server == "REAL":
            self.init(REST_HOST, proxy_host, proxy_port)
        else:
            self.init(TESTNET_REST_HOST, proxy_host, proxy_port)
        self.connect_time = (
                int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )
        self.start()
        self.query_contract()
        self.gateway.write_log("REST API启动成功")

    def _new_order_id(self) -> int:
        """"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        # 检查委托类型是否正确
        if req.type not in ORDER_TYPE_AB2BYBIT:
            self.gateway.write_log(f"委托失败，不支持的委托类型：{req.type.value}")
            return

        # 检查合约代码是否正确并根据合约类型判断下单接口
        if req.symbol in ubc_symbol_contract_map.keys():
            path: str = "/private/linear/order/create"
        else:
            self.gateway.write_log(f"委托失败，找不到该合约代码{req.symbol}")
            return

        # 生成本地委托号
        orderid = self.ORDER_PREFIX + \
                  str(self.connect_time + self._new_order_id())
        # 推送提交中事件
        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        order_type, time_in_force = ORDER_TYPE_AB2BYBIT[req.type]
        # 生成委托请求
        data: dict = {
            "symbol": req.symbol,
            "side": DIRECTION_AB2BYBIT[req.direction],
            "order_type": order_type,
            "price": req.price,
            "qty": req.volume,
            "order_link_id": orderid,
            "time_in_force": time_in_force,
            "reduce_only": False,
            "close_on_trigger": False
        }
        if self.position_mode == "MergedSingle":
            data["position_idx"] = 0

        if req.offset == Offset.CLOSE:
            data["reduce_only"] = True

        self.add_request(
            "POST",
            path,
            callback=self.on_send_order,
            data=data,
            extra=order,
            on_failed=self.on_send_order_failed,
            on_error=self.on_send_order_error,
        )

        self.gateway.on_order(order)
        return order.ab_orderid

    def on_send_order_failed(
            self,
            status_code: int,
            request: Request
    ) -> None:
        """委托下单失败服务器报错回报"""
        order: OrderData = request.extra
        order.status = Status.REJECTED
        order.reference = request.response.text
        self.gateway.on_order(order)

        data: dict = request.response.json()
        error_msg: str = data["ret_msg"]
        error_code: int = data["ret_code"]
        msg = f"委托失败，错误代码:{error_code},  错误信息：{error_msg}"
        self.gateway.write_log(data)

    def on_send_order_error(
            self,
            exception_type: type,
            exception_value: Exception,
            tb,
            request: Request
    ) -> None:
        """委托下单回报函数报错回报"""
        order: OrderData = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)

    def on_send_order(self, data: dict, request: Request) -> None:
        """委托下单回报"""
        if self.check_error("委托下单", data):
            order: OrderData = request.extra
            order.status = Status.REJECTED
            self.gateway.on_order(order)

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        # 检查合约代码是否正确并根据合约类型判断撤单接口
        if req.symbol in ubc_symbol_contract_map.keys():
            path: str = "/private/linear/order/cancel"
        else:
            self.gateway.write_log(f"撤单失败，找不到该合约代码{req.symbol}")
            return

        data: dict = {"symbol": req.symbol}

        # 检查是否为本地委托号
        if req.orderid in local_orderids:
            data["order_link_id"] = req.orderid
        else:
            data["order_id"] = req.orderid

        self.add_request(
            "POST",
            path,
            data=data,
            callback=self.on_cancel_order
        )

    def on_cancel_order(self, data: dict, request: Request) -> None:
        """委托撤单回报"""
        if data["ret_code"]:
            error_code: int = data["ret_code"]
            error_msg: str = data["ret_msg"]
            if error_code == 20001:
                order: OrderData = request.extra
                order.status = Status.REJECTED
                self.gateway.on_order(order)
            msg = f"撤单失败，错误代码：{error_code}，信息：{error_msg}"
            self.gateway.write_log(msg)
            return

    def on_failed(self, status_code: int, request: Request) -> None:
        """处理请求失败回报"""
        data: dict = request.response.json()
        error_msg: str = data["ret_msg"]
        error_code: int = data["ret_code"]

        msg = f"请求失败，状态码：{request.status}，错误代码：{error_code}, 信息：{error_msg}"
        self.gateway.write_log(msg)

    def on_query_position(self, data: dict, request: Request) -> None:
        """持仓查询回报"""
        if self.check_error("查询持仓", data):
            return

        data = data["result"]

        for d in data:
            d = d["data"]

            if d["size"]:
                position: PositionData = PositionData(
                    symbol=d["symbol"],
                    exchange=Exchange.BYBIT,
                    direction=Direction.NET if d["mode"] == "MergedSingle" else DIRECTION_BYBIT2AB[d["side"]],
                    volume=-d["size"] if d["side"] == "Sell" and d["mode"] == "MergedSingle" else d["size"],
                    price=float(d["entry_price"]),
                    liq_price=float(d["liq_price"]),
                    bust_price=float(d["bust_price"]),
                    gateway_name=self.gateway_name
                )
                self.gateway.on_position(position)

        self.gateway.on_raw(build_raw_data(data, self.gateway_name, "position"))

    def on_query_contract(self, data: dict, request: Request) -> None:
        """合约查询回报"""
        if self.check_error("查询合约", data):
            return

        for d in data["result"]:
            # 提取信息生成合约对象
            contract: ContractData = ContractData(
                symbol=d["name"],
                exchange=Exchange.BYBIT,
                name=d["name"],
                pricetick=float(d["price_filter"]["tick_size"]),
                size=1,
                step_size=d["lot_size_filter"]["qty_step"],
                min_volume=d["lot_size_filter"]["min_trading_qty"],
                product=Product.FUTURES,
                net_position=True,
                history_data=True,
                gateway_name=self.gateway_name
            )

            # 缓存正向永续合约信息并推送
            if d["quote_currency"] == "USDT":
                ubc_symbol_contract_map[contract.symbol] = contract
                self.gateway.on_contract(contract)

        self.gateway.write_log("合约信息查询成功")
        self.query_position()
        self.query_account()
        self.query_order()

    def on_query_account(self, data: dict, request: Request) -> None:
        """资金查询回报"""
        if self.check_error("查询账号", data):
            return

        for key, value in data["result"].items():
            if key == "USDT":
                account: AccountData = AccountData(
                    accountid=key,
                    balance=value["wallet_balance"],
                    frozen=value["used_margin"],
                    gateway_name=self.gateway_name,
                )
                self.gateway.on_account(account)
                self.gateway.write_log(f"{key}资金信息查询成功")

        self.gateway.on_raw(build_raw_data(data, self.gateway_name, "account"))

    def on_query_order(self, data: dict, request: Request):
        """未成交委托查询回报"""
        if self.check_error("查询委托", data):
            return

        if not data["result"]:
            return

        for d in data["result"]:
            orderid: str = d["order_link_id"]
            if orderid:
                local_orderids.add(orderid)
            else:
                orderid: str = d["order_id"]

            dt: datetime = generate_datetime(d["created_time"])

            order: OrderData = OrderData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                orderid=orderid,
                type=ORDER_TYPE_BYBIT2AB[d["order_type"]],
                direction=DIRECTION_BYBIT2AB[d["side"]],
                price=d["price"],
                volume=d["qty"],
                traded=d["cum_exec_qty"],
                status=STATUS_BYBIT2AB[d["order_status"]],
                datetime=dt,
                gateway_name=self.gateway_name
            )
            offset: bool = d["reduce_only"]
            if offset:
                order.offset = Offset.CLOSE
            else:
                order.offset = Offset.OPEN

            self.gateway.on_order(order)

        self.gateway.write_log(f"{order.symbol}委托信息查询成功")

        self.gateway.on_raw(build_raw_data(data, self.gateway_name, "order"))

    def query_contract(self) -> None:
        """查询合约信息"""
        self.add_request(
            "GET",
            "/v2/public/symbols",
            self.on_query_contract
        )

    def check_error(self, name: str, data: dict) -> bool:
        """回报状态检查"""
        if data["ret_code"]:
            error_code: int = data["ret_code"]
            error_msg: str = data["ret_msg"]
            msg = f"{name}失败，错误代码：{error_code}，信息：{error_msg}"
            self.gateway.write_log(msg)
            return True

        return False

    def query_account(self) -> None:
        """查询资金"""
        self.add_request(
            "GET",
            "/v2/private/wallet/balance",
            self.on_query_account
        )

    def query_position(self) -> None:
        """查询持仓"""
        path_usdt: str = "/private/linear/position/list"
        self.add_request(
            "GET",
            path_usdt,
            self.on_query_position
        )

    def query_order(self) -> None:
        """查询未成交委托"""
        path_usdt: str = "/private/linear/order/search"

        for symbol in ubc_symbol_contract_map.keys():
            params: dict = {
                "symbol": symbol
            }

            self.add_request(
                "GET",
                path_usdt,
                callback=self.on_query_order,
                params=params
            )

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        history: list = []
        count: int = 200
        start_time: int = int(req.start.timestamp())

        path: str = "/public/linear/kline"

        while True:
            # 创建查询参数
            params: dict = {
                "symbol": req.symbol,
                "interval": INTERVAL_AB2BYBIT[req.interval],
                "from": start_time,
                "limit": count
            }

            # 从服务器获取响应
            resp = self.request(
                "GET",
                path,
                params=params
            )

            # 如果请求失败则终止循环
            if resp.status_code // 100 != 2:
                msg = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg)
                break
            else:
                data: dict = resp.json()

                ret_code: int = data["ret_code"]
                if ret_code:
                    ret_msg: str = data["ret_msg"]
                    msg = f"获取历史数据出错，错误信息：{ret_msg}"
                    self.gateway.write_log(msg)
                    break

                if not data["result"]:
                    msg = f"获取历史数据为空，开始时间：{start_time}，数量：{count}"
                    self.gateway.write_log(msg)
                    break

                buf: list = []
                for d in data["result"]:
                    dt: datetime = generate_datetime_2(d["open_time"])

                    bar: BarData = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=dt,
                        interval=req.interval,
                        volume=float(d["volume"]),
                        open_price=float(d["open"]),
                        high_price=float(d["high"]),
                        low_price=float(d["low"]),
                        close_price=float(d["close"]),
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)

                history.extend(buf)

                begin: datetime = buf[0].datetime
                end: datetime = buf[-1].datetime
                msg = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # 收到最后数据则结束循环
                if len(buf) < count:
                    break

                # 更新开始时间
                start_time: int = int((bar.datetime + TIMEDELTA_MAP[req.interval]).timestamp())

        return history
    
    def query_lcp(self, symbol):
        path_usdt: str = "/v2/private/account/lcp"
        params: dict = {
            "symbol": symbol
        }

        self.add_request(
            "GET",
            path_usdt,
            print,
            params=params
        )


class BybitBBCAccessor(RestfulAccessor):
    "币本位永续、交割合约REST接口"
    ORDER_PREFIX = str(hex(uuid.getnode()))

    def __init__(self, gateway: Gateway):
        super(BybitBBCAccessor, self).__init__(gateway)

        self.gateway: Gateway = gateway

        self.key: str = ""
        self.secret: bytes = b""

        self.connect_time: int = 0

        self.order_count: int = 1_000_000
        self.order_count_lock: Lock = Lock()

    def sign(self, request: Request) -> Request:
        """生成签名"""
        request.headers = {"Referer": "abquant"}

        if request.method == "GET":
            api_params: dict = request.params
            if api_params is None:
                api_params = request.params = {}
        else:
            api_params: dict = request.data
            if api_params is None:
                api_params = request.data = {}

        api_params["api_key"] = self.key
        api_params["recv_window"] = 30 * 1000
        api_params["timestamp"] = generate_timestamp(-5)

        data2sign = "&".join([f"{k}={v}" for k, v in sorted(api_params.items())])
        signature: str = sign(self.secret, data2sign.encode())
        api_params["sign"] = signature

        return request

    def connect(
            self,
            key: str,
            secret: str,
            position_mode: str,
            server: str,
            proxy_host: str,
            proxy_port: int,
    ) -> None:
        """连接服务器"""
        self.key = key
        self.secret = secret.encode()

        if server == "REAL":
            self.init(REST_HOST, proxy_host, proxy_port)
        else:
            self.init(TESTNET_REST_HOST, proxy_host, proxy_port)
        self.connect_time = (
                int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )
        self.start()
        self.query_contract()
        self.gateway.write_log("REST API启动成功")

    def _new_order_id(self) -> int:
        """"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        # 检查委托类型是否正确
        if req.type not in ORDER_TYPE_AB2BYBIT:
            self.gateway.write_log(f"委托失败，不支持的委托类型：{req.type.value}")
            return

        # 检查合约代码是否正确并根据合约类型判断下单接口
        if req.symbol in bbc_symbol_contract_map:
            path: str = "/v2/private/order/create"
        elif req.symbol in future_symbol_contract_map:
            path: str = "/futures/private/order/create"
        else:
            self.gateway.write_log(f"委托失败，找不到该合约代码{req.symbol}")
            return

        # 生成本地委托号
        orderid = self.ORDER_PREFIX + \
                  str(self.connect_time + self._new_order_id())  # 推送提交中事件

        # 推送提交中事件
        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        order_type, time_in_force = ORDER_TYPE_AB2BYBIT[req.type]

        # 生成委托请求
        data: dict = {
            "symbol": req.symbol,
            "side": DIRECTION_AB2BYBIT[req.direction],
            "order_type": order_type,
            "price": req.price,
            "qty": int(req.volume),
            "order_link_id": orderid,
            "time_in_force": time_in_force,
            "reduce_only": False,
            "close_on_trigger": False
        }

        if req.offset == Offset.CLOSE:
            data["reduce_only"] = True

        self.add_request(
            "POST",
            path,
            callback=self.on_send_order,
            data=data,
            extra=order,
            on_failed=self.on_send_order_failed,
            on_error=self.on_send_order_error,
        )

        self.gateway.on_order(order)
        return order.ab_orderid

    def on_send_order_failed(
            self,
            status_code: int,
            request: Request
    ) -> None:
        """委托下单失败服务器报错回报"""
        order: OrderData = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        data: dict = request.response.json()
        error_msg: str = data["ret_msg"]
        error_code: int = data["ret_code"]
        msg = f"委托失败，错误代码:{error_code},  错误信息：{error_msg}"
        self.gateway.write_log(msg)

    def on_send_order_error(
            self,
            exception_type: type,
            exception_value: Exception,
            tb,
            request: Request
    ) -> None:
        """委托下单回报函数报错回报"""
        order: OrderData = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)

    def on_send_order(self, data: dict, request: Request) -> None:
        """委托下单回报"""
        if self.check_error("委托下单", data):
            order: OrderData = request.extra
            order.status = Status.REJECTED
            self.gateway.on_order(order)

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        # 检查合约代码是否正确并根据合约类型判断撤单接口
        if req.symbol in bbc_symbol_contract_map:
            path: str = "/v2/private/order/cancel"
        elif req.symbol in future_symbol_contract_map:
            path: str = "/futures/private/order/cancel"
        else:
            self.gateway.write_log(f"撤单失败，找不到该合约代码{req.symbol}")
            return

        data: dict = {"symbol": req.symbol}

        # 检查是否为本地委托号
        if req.orderid in local_orderids:
            data["order_link_id"] = req.orderid
        else:
            data["order_id"] = req.orderid

        self.add_request(
            "POST",
            path,
            data=data,
            callback=self.on_cancel_order
        )

    def on_cancel_order(self, data: dict, request: Request) -> None:
        """委托撤单回报"""
        
        if data["ret_code"]:
            error_code: int = data["ret_code"]
            error_msg: str = data["ret_msg"]
            if error_code == 20001:
                order: OrderData = request.extra
                order.status = Status.REJECTED
                self.gateway.on_order(order)
            msg = f"撤单失败，错误代码：{error_code}，信息：{error_msg}"
            self.gateway.write_log(msg)
            return

    def on_failed(self, status_code: int, request: Request) -> None:
        """处理请求失败回报"""
        data: dict = request.response.json()
        error_msg: str = data["ret_msg"]
        error_code: int = data["ret_code"]

        msg = f"请求失败，状态码：{request.status}，错误代码：{error_code}, 信息：{error_msg}"
        self.gateway.write_log(msg)

    def on_query_position(self, data: dict, request: Request) -> None:
        """持仓查询回报"""
        if self.check_error("查询持仓", data):
            return

        data = data["result"]
        for d_ in data:
            d = d_["data"]

            if d["position_idx"] == 0:
                direction = Direction.NET
            elif d["position_idx"] == 1:
                direction = Direction.LONG
            else:
                direction = Direction.SHORT
                
            position: PositionData = PositionData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                direction=direction,
                volume=-d["size"] if d["side"] == "Sell" and direction == Direction.NET else d["size"],
                price=float(d["entry_price"]),
                liq_price=float(d["liq_price"]),
                bust_price=float(d["bust_price"]),
                gateway_name=self.gateway_name
            )
            self.gateway.on_position(position)

        self.gateway.on_raw(build_raw_data(data, self.gateway_name, "account"))

    def on_query_contract(self, data: dict, request: Request) -> None:
        """合约查询回报"""
        if self.check_error("查询合约", data):
            return

        for d in data["result"]:
            # 提取信息生成合约对象
            contract: ContractData = ContractData(
                symbol=d["name"],
                exchange=Exchange.BYBIT,
                name=d["name"],
                pricetick=float(d["price_filter"]["tick_size"]),
                size=1,
                step_size=d["lot_size_filter"]["qty_step"],
                min_volume=d["lot_size_filter"]["min_trading_qty"],
                product=Product.FUTURES,
                net_position=True,
                history_data=True,
                gateway_name=self.gateway_name
            )

            # 缓存反向永续合约信息并推送
            if d["name"] == d["alias"] and d["quote_currency"] != "USDT":
                bbc_symbol_contract_map[contract.symbol] = contract
                self.gateway.on_contract(contract)
            # 缓存反向交割合约信息并推送
            elif d["name"] != d["alias"]:
                future_symbol_contract_map[contract.symbol] = contract
                self.gateway.on_contract(contract)

        self.gateway.write_log("合约信息查询成功")
        self.query_position()
        self.query_account()
        self.query_order()

    def on_query_account(self, data: dict, request: Request) -> None:
        """资金查询回报"""
        if self.check_error("查询账号", data):
            return

        for key, value in data["result"].items():
            if key != "USDT":
                account: AccountData = AccountData(
                    accountid=key,
                    balance=value["wallet_balance"],
                    frozen=value["used_margin"],
                    gateway_name=self.gateway_name,
                )
                self.gateway.on_account(account)
                self.gateway.write_log(f"{key}资金信息查询成功")

        self.gateway.on_raw(build_raw_data(data, self.gateway_name, "account"))

    def on_query_order(self, data: dict, request: Request):
        """未成交委托查询回报"""
        if self.check_error("查询委托", data):
            return

        if not data["result"]:
            return

        for d in data["result"]:
            orderid: str = d["order_link_id"]
            if orderid:
                local_orderids.add(orderid)
            else:
                orderid: str = d["order_id"]

            dt: datetime = generate_datetime(d["created_at"])

            order: OrderData = OrderData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                orderid=orderid,
                type=ORDER_TYPE_BYBIT2AB[d["order_type"]],
                direction=DIRECTION_BYBIT2AB[d["side"]],
                price=d["price"],
                volume=d["qty"],
                traded=d["cum_exec_qty"],
                status=STATUS_BYBIT2AB[d["order_status"]],
                datetime=dt,
                gateway_name=self.gateway_name
            )
            self.gateway.on_order(order)

        self.gateway.write_log(f"{order.symbol}委托信息查询成功")

        self.gateway.on_raw(build_raw_data(data, self.gateway_name, "account"))

    def query_contract(self) -> None:
        """查询合约信息"""
        self.add_request(
            "GET",
            "/v2/public/symbols",
            self.on_query_contract
        )

    def check_error(self, name: str, data: dict) -> bool:
        """回报状态检查"""
        if data["ret_code"]:
            error_code: int = data["ret_code"]
            error_msg: str = data["ret_msg"]
            msg = f"{name}失败，错误代码：{error_code}，信息：{error_msg}"
            self.gateway.write_log(msg)
            return True

        return False

    def query_account(self) -> None:
        """查询资金"""
        self.add_request(
            "GET",
            "/v2/private/wallet/balance",
            self.on_query_account
        )

    def query_position(self) -> None:
        """查询持仓"""
        path_swap: str = "/v2/private/position/list"
        self.add_request(
            "GET",
            path_swap,
            self.on_query_position
        )

        path_future: str = "/futures/private/position/list"
        self.add_request(
            "GET",
            path_future,
            self.on_query_position
        )

    def query_order(self) -> None:
        """查询未成交委托"""
        path_swap: str = "/v2/private/order"

        for symbol in bbc_symbol_contract_map.keys():
            params: dict = {
                "symbol": symbol
            }

            self.add_request(
                "GET",
                path_swap,
                callback=self.on_query_order,
                params=params
            )

        path_future: str = "/futures/private/order"

        for symbol in future_symbol_contract_map.keys():
            params: dict = {
                "symbol": symbol
            }

            self.add_request(
                "GET",
                path_future,
                callback=self.on_query_order,
                params=params
            )

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        history: list = []
        count: int = 200
        start_time: int = int(req.start.timestamp())

        path: str = "/v2/public/kline/list"

        while True:
            # 创建查询参数
            params: dict = {
                "symbol": req.symbol,
                "interval": INTERVAL_AB2BYBIT[req.interval],
                "from": start_time,
                "limit": count
            }

            # 从服务器获取响应
            resp = self.request(
                "GET",
                path,
                params=params
            )

            # 如果请求失败则终止循环
            if resp.status_code // 100 != 2:
                msg = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg)
                break
            else:
                data: dict = resp.json()

                ret_code: int = data["ret_code"]
                if ret_code:
                    ret_msg: str = data["ret_msg"]
                    msg = f"获取历史数据出错，错误信息：{ret_msg}"
                    self.gateway.write_log(msg)
                    break

                if not data["result"]:
                    msg = f"获取历史数据为空，开始时间：{start_time}，数量：{count}"
                    self.gateway.write_log(msg)
                    break

                buf: list = []
                for d in data["result"]:
                    dt: datetime = generate_datetime_2(d["open_time"])

                    bar: BarData = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=dt,
                        interval=req.interval,
                        volume=float(d["volume"]),
                        open_price=float(d["open"]),
                        high_price=float(d["high"]),
                        low_price=float(d["low"]),
                        close_price=float(d["close"]),
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)

                history.extend(buf)

                begin: datetime = buf[0].datetime
                end: datetime = buf[-1].datetime
                msg = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # 收到最后数据则结束循环
                if len(buf) < count:
                    break

                # 更新开始时间
                start_time: int = int((bar.datetime + TIMEDELTA_MAP[req.interval]).timestamp())

        return history

    
    def query_lcp(self, symbol):
        path: str = "/v2/private/account/lcp"
        params: dict = {
            "symbol": symbol
        }

        self.add_request(
            "GET",
            path,
            print,
            params=params
        )

