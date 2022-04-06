from threading import Lock
from logging import ERROR, WARNING
import sys
from typing import Iterable, List, Optional
from threading import Lock
import urllib.parse
import time
import hmac
import hashlib
from datetime import datetime
from requests.exceptions import SSLError
import uuid

from abquant.trader.utility import round_to

from . import DIRECTION_AB2BITMEX, INTERVAL_AB2BITMEX, ORDERTYPE_AB2BITMEX, REST_HOST, TESTNET_REST_HOST, TIMEDELTA_MAP, symbol_contract_map
from ..accessor import Request, RestfulAccessor
from ..basegateway import Gateway
from abquant.trader.msg import BarData, OrderData
from abquant.trader.common import Direction, Exchange, Offset, OrderType, Product, Status
from abquant.trader.object import AccountData, CancelRequest, ContractData, HistoryRequest, OrderRequest, PositionData




class BitmexAccessor(RestfulAccessor):
    """
    BitMEX REST API
    """

    def __init__(self, gateway: Gateway):
        """"""
        super(BitmexAccessor, self).__init__(gateway)

        self.key = ""
        self.secret = ""

        self.order_count = 1_000_000
        self.order_count_lock = Lock()

        self.connect_time = 0

        # Use 60 by default, and will update after first request
        self.rate_limit_limit = 60
        self.rate_limit_remaining = 60
        self.rate_limit_sleep = 0

    def sign(self, request: Request):
        """
        Generate BitMEX signature.
        """
        # Sign
        expires = int(time.time() + 5)

        if request.params:
            query = urllib.parse.urlencode(request.params)
            path = request.path + "?" + query
        else:
            path = request.path

        if request.data:
            request.data = urllib.parse.urlencode(request.data)
        else:
            request.data = ""

        msg = request.method + "/api/v1" + path + str(expires) + request.data
        signature = hmac.new(
            self.secret, msg.encode(), digestmod=hashlib.sha256
        ).hexdigest()

        # Add headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "api-key": self.key,
            "api-expires": str(expires),
            "api-signature": signature,
        }

        request.headers = headers
        return request

    def connect(
        self,
        key: str,
        secret: str,
        session_number: int,
        server: str,
        proxy_host: str,
        proxy_port: int,
    ):
        """
        Initialize connection to REST server.
        """
        self.key = key
        self.secret = secret.encode()

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        if server == "REAL":
            self.init(REST_HOST, proxy_host, proxy_port)
        else:
            self.init(TESTNET_REST_HOST, proxy_host, proxy_port)

        self.start(session_number)

        self.gateway.write_log("REST API启动成功")

    def _new_order_id(self):
        """"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest):
        """"""
        if not self.check_rate_limit():
            return ""

        orderid = str(self.connect_time + self._new_order_id())

        data = {
            "symbol": req.symbol,
            "side": DIRECTION_AB2BITMEX[req.direction],
            "ordType": ORDERTYPE_AB2BITMEX[req.type],
            "orderQty": int(req.volume),
            "clOrdID": orderid,
        }

        inst = []   # Order special instructions

        contract = symbol_contract_map.get(req.symbol)
        if contract:
            price_tick = contract.pricetick
            price = round_to(req.price, price_tick)
        else:
            self.gateway.write_log(f"找不到{req.symbol}对应的contract，请检查连接", level=WARNING)
            return ""

        # Only add price for limit order.
        if req.type == OrderType.LIMIT or req.type == OrderType.POSTONLYLIMIT:
            data["price"] = price
        elif req.type == OrderType.STOP_MARKET:
            data["stopPrice"] = price

        # stop ? TODO
        if req.offset == Offset.CLOSE:
            inst.append("ReduceOnly")
        elif req.type == OrderType.POSTONLYLIMIT:
            inst.append("ParticipateDoNotInitiate")

        if inst:
            data["execInst"] = ",".join(inst)

        order = req.create_order_data(orderid, self.gateway_name)

        self.add_request(
            "POST",
            "/order",
            callback=self.on_send_order,
            data=data,
            extra=order,
            on_failed=self.on_send_order_failed,
            on_error=self.on_send_order_error,
        )

        self.gateway.on_order(order)
        return order.ab_orderid

    def cancel_order(self, req: CancelRequest):
        """"""
        if not self.check_rate_limit():
            return

        orderid = req.orderid

        if orderid.isdigit():
            params = {"clOrdID": orderid}
        else:
            params = {"orderID": orderid}

        self.add_request(
            "DELETE",
            "/order",
            callback=self.on_cancel_order,
            params=params,
            on_failed=self.on_failed,
            on_error=self.on_cancel_order_error,
        )

    def query_history(self, req: HistoryRequest):
        """"""


        history = []
        count = 750
        start_time = req.start.isoformat()

        while True:
            # Create query params
            if not self.check_rate_limit():
                time.sleep(10)
                continue
            params = {
                "binSize": INTERVAL_AB2BITMEX[req.interval],
                "symbol": req.symbol,
                "count": count,
                "startTime": start_time
            }

            # Add end time if specified
            if req.end:
                params["endTime"] = req.end.isoformat()

            # Get response from server
            resp = self.request(
                "GET",
                "/trade/bucketed",
                params=params
            )

            # Break if request failed with other status code
            if resp.status_code // 100 != 2:
                msg = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg, level=ERROR)
                break
            else:
                headers = resp.headers
                self.rate_limit_remaining = int(headers.get("x-ratelimit-remaining", 60))

                self.rate_limit_sleep = int(headers.get("Retry-After", 0))
                if self.rate_limit_sleep:
                    self.rate_limit_sleep += 1

                data = resp.json()
                if not data:
                    msg = f"获取历史数据为空，开始时间：{start_time}，数量：{count}"
                    break

                for d in data:
                    bar = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=datetime.strptime(d["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ"),
                        interval=req.interval,
                        volume=d["volume"],
                        open_price=d["open"],
                        high_price=d["high"],
                        low_price=d["low"],
                        close_price=d["close"],
                        gateway_name=self.gateway_name
                    )
                    history.append(bar)

                begin = data[0]["timestamp"]
                end = data[-1]["timestamp"]
                msg = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # Break if total data count less than 750 (latest date collected)
                if len(data) < 750:
                    break

                # Update start time
                start_time = bar.datetime + TIMEDELTA_MAP[req.interval]

        return history

    def on_send_order_failed(self, status_code: str, request: Request):
        """
        Callback when sending order failed on server.
        """
        self.update_rate_limit(request)

        order = request.extra
        order.status = Status.REJECTED
        order.reference = request.response.text
        self.gateway.on_order(order)

        if request.response.text:
            data = request.response.json()
            error = data["error"]
            msg = f"委托失败，状态码：{status_code}，类型：{error['name']}, 信息：{error['message']}"
        else:
            msg = f"委托失败，状态码：{status_code}"

        self.gateway.write_log(msg)

    def on_send_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ):
        """
        Callback when sending order caused exception.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        # Record exception if not ConnectionError
        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)

    def on_send_order(self, data, request):
        """Websocket will push a new order status"""
        self.update_rate_limit(request)

    def on_cancel_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ):
        # Record exception if not ConnectionError
        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)

    def on_cancel_order(self, data, request):
        self.update_rate_limit(request)

    def on_failed(self, status_code: int, request: Request):
        self.update_rate_limit(request)

        data = request.response.json()
        error = data["error"]
        msg = f"请求失败，状态码：{status_code}，类型：{error['name']}, 信息：{error['message']}"
        self.gateway.write_log(msg, level=WARNING)

    def update_rate_limit(self, request: Request):
        if request.response is None:
            return
        headers = request.response.headers

        self.rate_limit_remaining = int(headers.get("x-ratelimit-remaining", 60))

        self.rate_limit_sleep = int(headers.get("Retry-After", 0))
        if self.rate_limit_sleep:
            self.rate_limit_sleep += 1      # 1 extra second sleep

    def reset_rate_limit(self):
        """
        Reset request limit remaining every 1 second.
        """
        self.rate_limit_remaining += 1
        self.rate_limit_remaining = min(
            self.rate_limit_remaining, self.rate_limit_limit)

        # Countdown of retry sleep seconds
        if self.rate_limit_sleep:
            self.rate_limit_sleep -= 1

    def check_rate_limit(self):
        # Already received 429 from server
        if self.rate_limit_sleep:
            msg = f"请求过于频繁，已被BitMEX限制，请等待{self.rate_limit_sleep}秒后再试"
            self.gateway.write_log(msg)
            return False
        # Just local request limit is reached
        elif not self.rate_limit_remaining:
            msg = "请求频率太高，有触发BitMEX流控的风险，请稍候再试"
            self.gateway.write_log(msg)
            return False
        else:
            self.rate_limit_remaining -= 1
            return True
