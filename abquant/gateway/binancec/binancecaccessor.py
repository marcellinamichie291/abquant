from logging import DEBUG, ERROR, WARNING
import sys
import threading
from typing import Iterable, List, Optional
from threading import Lock
import urllib.parse
import time
import hmac
import hashlib
from datetime import datetime
from requests.api import request
from requests.exceptions import SSLError
import uuid
from requests.models import MissingSchema

from . import DIRECTION_AB2BINANCEC, DIRECTION_BINANCEC2AB, D_REST_HOST, D_TESTNET_RESTT_HOST, D_TESTNET_WEBSOCKET_TRADE_HOST, D_WEBSOCKET_TRADE_HOST, F_REST_HOST, F_TESTNET_RESTT_HOST, F_TESTNET_WEBSOCKET_TRADE_HOST, F_WEBSOCKET_TRADE_HOST, INTERVAL_AB2BINANCEC, ORDERTYPE_AB2BINANCEC, ORDERTYPE_BINANCEC2AB, STATUS_BINANCEC2AB, TIMEDELTA_MAP, Security, symbol_contract_map
from .binanceclistener import BinanceCTradeWebsocketListener
from ..accessor import Request, RestfulAccessor
from ..basegateway import Gateway
from abquant.trader.msg import BarData, OrderData
from abquant.trader.utility import round_to
from abquant.trader.common import Direction, Exchange, Offset, OrderType, Product, Status
from abquant.trader.object import AccountData, CancelRequest, ContractData, HistoryRequest, OrderRequest, PositionData


class BinanceCAccessor(RestfulAccessor):

    ORDER_PREFIX = str(hex(uuid.getnode()))

    def __init__(self, gateway: Gateway):
        """"""
        super(BinanceCAccessor, self).__init__(gateway)

        self.trade_listener: BinanceCTradeWebsocketListener = self.gateway.trade_listener

        self.key: str = ""
        self.secret: str = ""

        self.user_stream_key: str = ""
        self.keep_alive_count: int = 0
        self.recv_window: int = 5000
        self.time_offset: int = 0

        self.order_count: int = 1_000_000
        self.order_count_lock: Lock = Lock()
        self.connect_time: int = 0
        self.usdt_base: bool = None

        self.server_datetime: datetime = datetime.now()
        self.rate_limit_lock: Lock = Lock()
        self.request_limit = 2400
        self.minite_orders_limit = 1200
        self.seconds_orders_limit = 300

        self.request_used = 0
        self.minite_orders_used = 0
        self.seconds_orders_used = 0

    def sign(self, request: Request) -> Request:
        security = request.data["security"]
        if security == Security.NONE:
            request.data = None
            return request

        if request.params:
            path = request.path + "?" + urllib.parse.urlencode(request.params)
        else:
            request.params = dict()
            path = request.path

        if security == Security.SIGNED:
            timestamp = int(time.time() * 1000)

            if self.time_offset > 0:
                timestamp -= abs(self.time_offset)
            elif self.time_offset < 0:
                timestamp += abs(self.time_offset)

            request.params["timestamp"] = timestamp

            query = urllib.parse.urlencode(sorted(request.params.items()))
            signature = hmac.new(self.secret, query.encode(
                "utf-8"), hashlib.sha256).hexdigest()

            query += "&signature={}".format(signature)
            path = request.path + "?" + query

        request.path = path
        request.params = {}
        request.data = {}

        # Add headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "X-MBX-APIKEY": self.key,
            "Connection": "close"
        }

        if security in [Security.SIGNED, Security.API_KEY]:
            request.headers = headers

        return request

    def connect(
        self,
        usdt_base: bool,
        key: str,
        secret: str,
        session_number: int,
        server: str,
        proxy_host: str,
        proxy_port: int
    ) -> None:
        """
        Initialize connection to REST server.
        """
        self.usdt_base = usdt_base
        self.key = key
        self.secret = secret.encode()
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host
        self.server = server

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        if self.server == "REAL":
            if self.usdt_base:
                self.init(F_REST_HOST, proxy_host, proxy_port)
            else:
                self.init(D_REST_HOST, proxy_host, proxy_port)
        else:
            if self.usdt_base:
                self.init(F_TESTNET_RESTT_HOST, proxy_host, proxy_port)
            else:
                self.init(D_TESTNET_RESTT_HOST, proxy_host, proxy_port)

        self.start(session_number)

        self.gateway.write_log("REST API启动成功")

        self.query_time()
        self.query_account()
        self.query_rate_limit()
        self.query_position()
        self.query_order()
        self.query_contract()
        self.start_user_stream()

    def query_time(self) -> Request:
        """"""
        data = {
            "security": Security.NONE
        }

        if self.usdt_base:
            path = "/fapi/v1/time"
        else:
            path = "/dapi/v1/time"

        return self.add_request(
            "GET",
            path,
            callback=self.on_query_time,
            data=data
        )

    def query_account(self) -> Request:
        """"""
        data = {"security": Security.SIGNED}

        if self.usdt_base:
            path = "/fapi/v1/account"
        else:
            path = "/dapi/v1/account"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_account,
            data=data
        )

    def query_rate_limit(self) -> Request:
        """"""
        data = {
            "security": Security.SIGNED
        }

        if self.usdt_base:
            path = "/fapi/v1/exchangeInfo"
        else:
            path = "/dapi/v1/exchangeInfo"

        return self.add_request(
            "GET",
            path,
            callback=self.on_query_rate_limit,
            data=data
        )

    def query_position(self) -> Request:
        """"""
        data = {"security": Security.SIGNED}

        if self.usdt_base:
            path = "/fapi/v1/positionRisk"
        else:
            path = "/dapi/v1/positionRisk"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_position,
            data=data
        )

    def query_order(self) -> Request:
        """"""
        data = {"security": Security.SIGNED}

        if self.usdt_base:
            path = "/fapi/v1/openOrders"
        else:
            path = "/dapi/v1/openOrders"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_order,
            data=data
        )

    def query_contract(self) -> Request:
        """"""
        data = {
            "security": Security.NONE
        }

        if self.usdt_base:
            path = "/fapi/v1/exchangeInfo"
        else:
            path = "/dapi/v1/exchangeInfo"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_contract,
            data=data
        )

    def _new_order_id(self) -> int:
        """"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest) -> str:
        """"""
        if not self.check_rate_limit(request=1, order=1):
            return ""
        orderid = self.ORDER_PREFIX + \
            str(self.connect_time + self._new_order_id())
        order = req.create_order_data(
            orderid,
            self.gateway_name
        )
        self.gateway.on_order(order)

        data = {
            "security": Security.SIGNED
        }

        order_type, time_condition = ORDERTYPE_AB2BINANCEC[req.type]

        contract = symbol_contract_map.get(req.symbol)
        if contract:
            price_tick = contract.pricetick
            price = round_to(req.price, price_tick)
            volume = round_to(req.volume, contract.step_size)


        params = {
            "symbol": req.symbol,
            "side": DIRECTION_AB2BINANCEC[req.direction],
            "type": order_type,
            "price": float(price),
            "quantity": float(volume),
            "newClientOrderId": orderid,
            "timeInForce": time_condition
        }
        # if time_condition:
        #     params['timeInForce'] = time_condition
        if req.type == OrderType.MARKET:
            params.pop('timeInForce')
            params.pop('price')
        if req.offset == Offset.CLOSE:
            params["reduceOnly"] = True

        if self.usdt_base:
            path = "/fapi/v1/order"
        else:
            path = "/dapi/v1/order"

        self.add_request(
            method="POST",
            path=path,
            callback=self.on_send_order,
            data=data,
            params=params,
            extra=order,
            on_error=self.on_send_order_error,
            on_failed=self.on_send_order_failed
        )

        return order.ab_orderid

    def cancel_order(self, req: CancelRequest) -> Request:
        """"""
        if not self.check_rate_limit(request=1, order=0):
            return
        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol,
            "origClientOrderId": req.orderid
        }

        if self.usdt_base:
            path = "/fapi/v1/order"
        else:
            path = "/dapi/v1/order"

        self.add_request(
            method="DELETE",
            path=path,
            callback=self.on_cancel_order,
            params=params,
            data=data,
            extra=req
        )

    def start_user_stream(self) -> Request:
        """"""
        data = {
            "security": Security.API_KEY
        }

        if self.usdt_base:
            path = "/fapi/v1/listenKey"
        else:
            path = "/dapi/v1/listenKey"

        self.add_request(
            method="POST",
            path=path,
            callback=self.on_start_user_stream,
            data=data
        )

    def keep_user_stream(self, interval) -> Request:
        """"""
        self.keep_alive_count += interval
        if self.keep_alive_count < 600:
            return
        self.keep_alive_count = 0

        data = {
            "security": Security.API_KEY
        }

        if self.usdt_base:
            path = "/fapi/v1/listenKey"
        else:
            path = "/dapi/v1/listenKey"
        self.add_request(
            method="POST",
            path=path,
            callback=self.on_keep_user_stream,
            # params=params,
            data=data
        )

    def on_query_time(self, data: dict, request: Request) -> None:
        """"""
        local_time = int(time.time() * 1000)
        server_time = int(data["serverTime"])
        self.time_offset = local_time - server_time

    def on_query_account(self, data: dict, request: Request) -> None:
        """"""
        for asset in data["assets"]:
            account = AccountData(
                accountid=asset["asset"],
                balance=float(asset["walletBalance"]),
                frozen=float(asset["maintMargin"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

        self.gateway.write_log("账户资金查询成功")

    def on_query_rate_limit(self, data: dict, request: Request) -> None:

        for rateLimits in data['rateLimits']:
            if rateLimits['rateLimitType'] == 'REQUEST_WEIGHT':
                self.request_limit = rateLimits['limit']
            elif rateLimits['rateLimitType'] == 'ORDERS':
                if rateLimits['interval'] == 'MINUTE':
                    self.minite_orders_limit = rateLimits['limit']
                elif rateLimits['interval'] == 'SECOND':
                    self.seconds_orders_limit = rateLimits['limit']


    def on_query_position(self, data: dict, request: Request) -> None:
        """"""
        for d in data:
            position = PositionData(
                symbol=d["symbol"],
                exchange=Exchange.BINANCE,
                direction=Direction.NET,
                volume=float(d["positionAmt"]),
                price=float(d["entryPrice"]),
                pnl=float(d["unRealizedProfit"]),
                gateway_name=self.gateway_name,
            )

            if position.volume:
                volume = d["positionAmt"]
                if '.' in volume:
                    position.volume = float(d["positionAmt"])
                else:
                    position.volume = int(d["positionAmt"])

                self.gateway.on_position(position)

        self.gateway.write_log("持仓信息查询成功")

    def on_query_order(self, data: dict, request: Request) -> None:
        """"""
        for d in data:
            key = (d["type"], d["timeInForce"])
            order_type = ORDERTYPE_BINANCEC2AB.get(key, None)
            if not order_type:
                continue

            order = OrderData(
                orderid=d["clientOrderId"],
                symbol=d["symbol"],
                exchange=Exchange.BINANCE,
                price=float(d["price"]),
                volume=float(d["origQty"]),
                type=order_type,
                direction=DIRECTION_BINANCEC2AB[d["side"]],
                traded=float(d["executedQty"]),
                status=STATUS_BINANCEC2AB.get(d["status"], None),
                datetime=datetime.fromtimestamp(d["time"] / 1000),
                gateway_name=self.gateway_name,
            )
            self.gateway.on_order(order)

        self.gateway.write_log("交易单信息查询成功")

    def on_query_contract(self, data: dict, request: Request) -> None:
        for d in data["symbols"]:
            base_currency = d["baseAsset"]
            quote_currency = d["quoteAsset"]
            name = f"{base_currency.upper()}/{quote_currency.upper()}"

            pricetick = 1
            min_volume = 1

            for f in d["filters"]:
                if f["filterType"] == "PRICE_FILTER":
                    pricetick = float(f["tickSize"])
                elif f["filterType"] == "LOT_SIZE":
                    stepSize = float(f["stepSize"])
                    min_volume = float(f["minQty"])

            contract = ContractData(
                symbol=d["symbol"],
                exchange=Exchange.BINANCE,
                name=name,
                pricetick=pricetick,
                size=1,
                step_size=stepSize,
                min_volume=min_volume,
                product=Product.FUTURES,
                net_position=True,
                history_data=True,
                on_board=datetime.fromtimestamp(d["onboardDate"] / 1000),
                gateway_name=self.gateway_name,
            )
            self.gateway.on_contract(contract)

            symbol_contract_map[contract.symbol] = contract

        self.gateway.write_log("交易所支持合约信息查询成功")

    def on_send_order(self, data: dict, request: Request) -> None:
        """"""
        self.update_rate_limit(request)

    def on_send_order_failed(self, status_code: str, request: Request) -> None:
        """
        Callback when sending order failed on server.
        """
        self.update_rate_limit(request)
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        msg = f"委托失败，状态码：{status_code}，信息：{request.response.text}, 当前servertime: {self.server_datetime}"
        self.gateway.write_log(msg, level=WARNING)

    def on_send_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ) -> None:
        """
        Callback when sending order caused exception.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        # Record exception if not ConnectionError
        if not issubclass(exception_type, (ConnectionError, SSLError)):
            self.on_error(exception_type, exception_value, tb, request)

    def on_cancel_order(self, data: dict, request: Request) -> None:
        """"""
        self.update_rate_limit(request)

    def on_failed(self, status_code: int, request: Request):
        self.update_rate_limit(request)
        super(BinanceCAccessor, self).on_failed(status_code, request)

    def on_start_user_stream(self, data: dict, request: Request) -> None:
        """"""
        self.user_stream_key = data["listenKey"]
        self.keep_alive_count = 0

        if self.server == "REAL":
            url = F_WEBSOCKET_TRADE_HOST + self.user_stream_key
            if not self.usdt_base:
                url = D_WEBSOCKET_TRADE_HOST + self.user_stream_key
        else:
            url = F_TESTNET_WEBSOCKET_TRADE_HOST + self.user_stream_key
            if not self.usdt_base:
                url = D_TESTNET_WEBSOCKET_TRADE_HOST + self.user_stream_key

        self.trade_listener.connect(url, self.proxy_host, self.proxy_port)

    def on_keep_user_stream(self, data: dict, request: Request) -> None:
        """"""
        if self.user_stream_key != data["listenKey"]:
            self.on_start_user_stream(data, request)

    def reset_server_time(self, interval: int):

        # conservative time trick.
        server_datetime = datetime.fromtimestamp(
            time.time() - self.time_offset / 1000 - 3)
        self.gateway.write_log("threadid {}: begin to reset ratelimt: request used: {}, seconds_userd: {}, minite_used: {}".format(threading.get_ident(), self.request_used, self.seconds_orders_used, self.minite_orders_used), level=DEBUG)
        with self.rate_limit_lock:
            if server_datetime.second // 10 != self.server_datetime.second // 10:
                self.gateway.write_log("reset second limit", level=DEBUG)
                self.seconds_orders_used = 0
            if server_datetime.minute != self.server_datetime.minute:
                self.minite_orders_used = 0
                self.request_used = 0
            self.server_datetime = server_datetime
        self.gateway.write_log("threadid: {}, after reset ratelimt: request used: {}, seconds_userd: {}, minite_used: {};;; server_datetime: {}".format(threading.get_ident(), self.request_used, self.seconds_orders_used, self.minite_orders_used, server_datetime), level=DEBUG)

    def check_rate_limit(self, request: int = 1, order: int = 0) -> bool:
        session_number = self.get_session_number()
        with self.rate_limit_lock:
            self.seconds_orders_used += order
            self.minite_orders_used += order
            self.request_used += request

            if self.seconds_orders_used + session_number > self.seconds_orders_limit:
                self.gateway.write_log("threadid: {}, check rate limit: request used: {}, seconds_userd: {}, minite_used: {}".format(threading.get_ident(), self.request_used, self.seconds_orders_used, self.minite_orders_used), level=DEBUG)
                msg = f"下单过于频繁，已被Binance限制, 10s内尝试下单{self.seconds_orders_used}, 可能超过{self.seconds_orders_limit}次每10s的限制， 该次订单被拦截。当前servertime: {self.server_datetime}"
                self.gateway.write_log(msg, level=WARNING)
                return False
            if self.minite_orders_used + session_number > self.minite_orders_limit:
                msg = f"下单过于频繁，已被Binance限制, 分钟内尝试下单{self.minite_orders_used}，可能超过{self.seconds_orders_limit}次每分钟的限制。该次订单被拦截。"
                self.gateway.write_log(msg, level=WARNING)
                return False
            if self.request_used + session_number > self.request_limit:
                msg = f"请求过于频繁，已被Binance限制, 分钟内试图请求{self.request_used}，可能超过{self.request_limit}次每分钟的限制。该次请求被拦截。"
                self.gateway.write_log(msg, level=WARNING)
                return False
        return True

    def update_rate_limit(self, request: Request):
        if request.response is None:
            return
        headers = request.response.headers
        self.gateway.write_log("threadid: {}, HTTP method: {} update_ rate limit: request used: {}, seconds_userd: {}, minite_used: {}".format(threading.get_ident(), request.method, self.request_used, self.seconds_orders_used, self.minite_orders_used), level=DEBUG)

        with self.rate_limit_lock:
            self.request_used = int(headers.get("X-MBX-USED-WEIGHT-1M", 0))
            minite_orders_used = headers.get("X-MBX-ORDER-COUNT-1M", None)
            if minite_orders_used is not None:
                self.minite_orders_used = int(minite_orders_used)
            seconds_orders_used = headers.get("X-MBX-ORDER-COUNT-10S", None)
            if seconds_orders_used is not None:
                self.seconds_orders_used = int(seconds_orders_used)

    def query_history(self, req: HistoryRequest) -> Iterable[BarData]:
        """"""


        history = []
        limit = 1500
        if self.usdt_base:
            start_time = int(datetime.timestamp(req.start))
        else:
            end_time = int(datetime.timestamp(req.end))

        while True:
            # Create query params
            params = {
                "symbol": req.symbol,
                "interval": INTERVAL_AB2BINANCEC[req.interval],
                "limit": limit
            }
            if not self.check_rate_limit(request=10, order=0):
                self.gateway.write_log("retry query history after 10s. Don't worry, rate limit will be check before request sending.")
                time.sleep(10)
                continue

            if self.usdt_base:
                params["startTime"] = start_time * 1000
                path = "/fapi/v1/klines"
                if req.end:
                    end_time = int(datetime.timestamp(req.end))
                    params["endTime"] = end_time * 1000
            else:
                params["endTime"] = end_time * 1000
                path = "/dapi/v1/klines"
                if req.start:
                    start_time = int(datetime.timestamp(req.start))
                    params["startTime"] = start_time * 1000
            try:
                resp = self.request(
                    "GET",
                    path=path,
                    data={"security": Security.NONE},
                    params=params
                )
            except MissingSchema as e:
                et, ev, tb = sys.exc_info()
                self.on_error(et, ev, tb, req)
                raise ConnectionError(
                    "call the gateway.connect method before trying to query history data. otherwaise UBC or BBC gateway is unknown.")
            # Break if request failed with other status code
            if resp.status_code // 100 != 2:
                msg = f"获取历史数据可能失败(也可能是自然终止)，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg, level=WARNING)
                break
            else:
                headers = resp.headers

                self.request_used = int(headers.get("X-MBX-USED-WEIGHT-1M", 0))
                data = resp.json()
                if not data:
                    msg = f"获取历史数据为空，开始时间：{start_time}"
                    self.gateway.write_log(msg, level=WARNING)
                    break

                buf = []

                for l in data:
                    bar = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=datetime.fromtimestamp(l[0] / 1000),
                        interval=req.interval,
                        volume=float(l[5]),
                        open_price=float(l[1]),
                        high_price=float(l[2]),
                        low_price=float(l[3]),
                        close_price=float(l[4]),
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)

                begin = buf[0].datetime
                end = buf[-1].datetime

                if not self.usdt_base:
                    buf = list(reversed(buf))
                history.extend(buf)
                msg = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # Break if total data count less than limit (latest date collected)
                if len(data) < limit:
                    break

                # Update start time
                if self.usdt_base:
                    start_dt = bar.datetime + TIMEDELTA_MAP[req.interval]
                    start_time = int(datetime.timestamp(start_dt))
                    if start_dt > req.end:
                        break
                # Update end time
                else:
                    end_dt = begin - TIMEDELTA_MAP[req.interval]
                    end_time = int(datetime.timestamp(end_dt))

        if not self.usdt_base:
            history = list(reversed(history))
        return history
