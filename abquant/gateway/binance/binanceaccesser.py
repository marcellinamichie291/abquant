from threading import Lock
import urllib
import time
import hashlib
import hmac
from copy import copy
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
import pytz

from . import DIRECTION_AB2BINANCE, DIRECTION_BINANCE2VT, REST_HOST
from abquant.gateway.accessor import RestfulAccessor
from abquant.gateway.basegateway import Gateway
from abquant.trader.object import OrderRequest


class BinanceAccessor(RestfulAccessor):


    def __init__(self, gateway: Gateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

        self.trade_ws_api = self.gateway.trade_ws_api

        self.key = ""
        self.secret = ""

        self.user_stream_key = ""
        self.keep_alive_count = 0
        self.recv_window = 5000
        self.time_offset = 0

        self.order_count = 1_000_000
        self.order_count_lock = Lock()
        self.connect_time = 0

    def sign(self, request):


        # TODO 
        query = urllib.parse.urlencode(sorted(request.params.items()))
        signature = hmac.new(self.secret, query.encode(
            "utf-8"), hashlib.sha256).hexdigest()

        query += "&signature={}".format(signature)
        path = request.path + "?" + query


        return request

    def connect(
        self,
        key: str,
        secret: str,
        session_number: int,
        proxy_host: str,
        proxy_port: int
    ):

        self.key = key
        self.secret = secret.encode()
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        self.init(REST_HOST, proxy_host, proxy_port)
        self.start(session_number)

        self.gateway.write_log("BINANCE restful accessor start")

        self.query_time()
        self.query_account()
        self.query_order()
        self.query_contract()
        self.start_user_stream()

    def query_time(self):
        """"""
        data = {
            "security": Security.NONE
        }
        path = "/api/v1/time"

        return self.add_request(
            "GET",
            path,
            callback=self.on_query_time,
            data=data
        )

    def query_account(self):
        """"""
        data = {}

        self.add_request(
            method="GET",
            path="/api/v3/account",
            callback=self.on_query_account,
            data=data
        )



    def _new_order_id(self):
        """"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest):
        """"""
        orderid = "NKD8FYX4-" + str(self.connect_time + self._new_order_id())
        order = req.create_order_data(
            orderid,
            self.gateway_name
        )
        self.gateway.on_order(order)

        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol.upper(),
            "timeInForce": "GTC",
            "side": DIRECTION_VT2BINANCE[req.direction],
            "type": ORDERTYPE_VT2BINANCE[req.type],
            "price": str(req.price),
            "quantity": str(req.volume),
            "newClientOrderId": orderid,
            "newOrderRespType": "ACK"
        }

        self.add_request(
            method="POST",
            path="/api/v3/order",
            callback=self.on_send_order,
            data=data,
            params=params,
            extra=order,
            on_error=self.on_send_order_error,
            on_failed=self.on_send_order_failed
        )

        return order.vt_orderid

    def cancel_order(self, req: CancelRequest):
        """"""
        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol.upper(),
            "origClientOrderId": req.orderid
        }

        self.add_request(
            method="DELETE",
            path="/api/v3/order",
            callback=self.on_cancel_order,
            params=params,
            data=data,
            extra=req
        )

    def start_user_stream(self):
        """"""
        data = {
            "security": Security.API_KEY
        }

        self.add_request(
            method="POST",
            path="/api/v1/userDataStream",
            callback=self.on_start_user_stream,
            data=data
        )

    def keep_user_stream(self):
        """"""
        self.keep_alive_count += 1
        if self.keep_alive_count < 600:
            return
        self.keep_alive_count = 0

        data = {
            "security": Security.API_KEY
        }

        params = {
            "listenKey": self.user_stream_key
        }

        self.add_request(
            method="PUT",
            path="/api/v1/userDataStream",
            callback=self.on_keep_user_stream,
            params=params,
            data=data
        )

    def on_query_time(self, data, request):
        """"""
        local_time = int(time.time() * 1000)
        server_time = int(data["serverTime"])
        self.time_offset = local_time - server_time

    def on_query_account(self, data, request):
        """"""
        for account_data in data["balances"]:
            account = AccountData(
                accountid=account_data["asset"],
                balance=float(account_data["free"]) + float(account_data["locked"]),
                frozen=float(account_data["locked"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

        self.gateway.write_log("账户资金查询成功")

    def on_query_order(self, data, request):
        """"""
        for d in data:
            order = OrderData(
                orderid=d["clientOrderId"],
                symbol=d["symbol"].lower(),
                exchange=Exchange.BINANCE,
                price=float(d["price"]),
                volume=float(d["origQty"]),
                type=ORDERTYPE_BINANCE2VT[d["type"]],
                direction=DIRECTION_BINANCE2VT[d["side"]],
                traded=float(d["executedQty"]),
                status=STATUS_BINANCE2VT.get(d["status"], None),
                datetime=generate_datetime(d["time"]),
                gateway_name=self.gateway_name,
            )
            self.gateway.on_order(order)

        self.gateway.write_log("委托信息查询成功")

    def on_query_contract(self, data, request):
        """"""
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
                    min_volume = float(f["stepSize"])

            contract = ContractData(
                symbol=d["symbol"].lower(),
                exchange=Exchange.BINANCE,
                name=name,
                pricetick=pricetick,
                size=1,
                min_volume=min_volume,
                product=Product.SPOT,
                history_data=True,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_contract(contract)

            symbol_name_map[contract.symbol] = contract.name

        self.gateway.write_log("合约信息查询成功")

    def on_send_order(self, data, request):
        """"""
        pass

    def on_send_order_failed(self, status_code: str, request: Request):
        """
        Callback when sending order failed on server.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        msg = f"委托失败，状态码：{status_code}，信息：{request.response.text}"
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
        if not issubclass(exception_type, (ConnectionError, SSLError)):
            self.on_error(exception_type, exception_value, tb, request)

    def on_cancel_order(self, data, request):
        """"""
        pass

    def on_start_user_stream(self, data, request):
        """"""
        self.user_stream_key = data["listenKey"]
        self.keep_alive_count = 0
        url = WEBSOCKET_TRADE_HOST + self.user_stream_key

        self.trade_ws_api.connect(url, self.proxy_host, self.proxy_port)

    def on_keep_user_stream(self, data, request):
        """"""
        pass

    def query_history(self, req: HistoryRequest):
        """"""
        history = []
        limit = 1000
        start_time = int(datetime.timestamp(req.start))

        while True:
            # Create query params
            params = {
                "symbol": req.symbol.upper(),
                "interval": INTERVAL_VT2BINANCE[req.interval],
                "limit": limit,
                "startTime": start_time * 1000,         # convert to millisecond
            }

            # Add end time if specified
            if req.end:
                end_time = int(datetime.timestamp(req.end))
                params["endTime"] = end_time * 1000     # convert to millisecond

            # Get response from server
            resp = self.request(
                "GET",
                "/api/v1/klines",
                data={"security": Security.NONE},
                params=params
            )

            # Break if request failed with other status code
            if resp.status_code // 100 != 2:
                msg = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg)
                break
            else:
                data = resp.json()
                if not data:
                    msg = f"获取历史数据为空，开始时间：{start_time}"
                    self.gateway.write_log(msg)
                    break

                buf = []

                for l in data:
                    bar = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=generate_datetime(l[0]),
                        interval=req.interval,
                        volume=float(l[5]),
                        open_price=float(l[1]),
                        high_price=float(l[2]),
                        low_price=float(l[3]),
                        close_price=float(l[4]),
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)

                history.extend(buf)

                begin = buf[0].datetime
                end = buf[-1].datetime
                msg = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # Break if total data count less than limit (latest date collected)
                if len(data) < limit:
                    break

                # Update start time
                start_dt = bar.datetime + TIMEDELTA_MAP[req.interval]
                start_time = int(datetime.timestamp(start_dt))

        return history

