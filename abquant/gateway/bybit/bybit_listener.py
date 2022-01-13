from datetime import datetime
from typing import Any, Callable, Dict
from copy import copy

from abquant.trader.common import Direction, Exchange, Offset
from abquant.trader.msg import DepthData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import AccountData, PositionData, SubscribeRequest
from ..basegateway import Gateway
from ..listener import WebsocketListener

from . import (
    DIRECTION_BYBIT2AB,
    INVERSE_WEBSOCKET_HOST,
    ORDER_TYPE_BYBIT2AB,
    PRIVATE_WEBSOCKET_HOST,
    PUBLIC_WEBSOCKET_HOST,
    STATUS_BYBIT2AB,
    TESTNET_INVERSE_WEBSOCKET_HOST,
    TESTNET_PRIVATE_WEBSOCKET_HOST,
    TESTNET_PUBLIC_WEBSOCKET_HOST,
    local_orderids,
    ubc_symbol_contract_map,
    bbc_symbol_contract_map,
    future_symbol_contract_map
)

from .bybit_util import generate_datetime, generate_datetime_2, generate_timestamp, get_float_value, sign


class BybitUBCMarketWebsocketListener(WebsocketListener):
    """U本位合约的行情Websocket接口"""

    def __init__(self, gateway: Gateway) -> None:
        """构造函数"""
        super(BybitUBCMarketWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 30

        self.ticks: Dict[str, TickData] = {}
        self.transactions: Dict[str, TransactionData] = {}
        self.depths: Dict[str, DepthData] = {}

        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.symbol_bids: Dict[str, dict] = {}
        self.symbol_asks: Dict[str, dict] = {}

    def connect(self, server: str, proxy_host: str, proxy_port: int):
        """ws行情"""

        if server == "REAL":
            url = PUBLIC_WEBSOCKET_HOST
        else:
            url = TESTNET_PUBLIC_WEBSOCKET_HOST
        self.init(url, proxy_host, proxy_port)

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接成功")

        for req in list(self.subscribed.values()):
            self.subscribe(req)

    def on_disconnected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接断开")

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""

        if req.symbol not in ubc_symbol_contract_map:
            self.gateway.write_log(f"找不到该合约代码{req.symbol}")
            return
        # 缓存订阅记录
        self.subscribed[req.symbol] = req

        symbol = req.symbol

        tick, depth, transaction, _ = self.make_data(symbol, Exchange.BYBIT, datetime.now(), self.gateway_name)
        self.ticks[symbol] = tick
        self.transactions[symbol] = transaction
        self.depths[symbol] = depth

        # 发送订阅请求
        subscribe_mode = self.gateway.subscribe_mode
        channels = []
        if subscribe_mode.best_tick:
            channels.append(f"instrument_info.100ms.{symbol}")
        if subscribe_mode.tick_5:
            channels.append(f"orderBookL2_25.{symbol}")
        if subscribe_mode.transaction:
            channels.append(f"trade.{symbol}")
        if subscribe_mode.depth:
            channels.append(f"orderBook_200.100ms.{symbol}")

        req_dict: dict = {
            "op": "subscribe",
            "args": channels
        }
        self.send_packet(req_dict)

    def on_packet(self, packet: dict):
        if "topic" not in packet:
            return
        channel: str = packet["topic"]

        if "instrument_info" in channel:
            # best_tick
            type_: str = packet["type"]
            data: dict = packet["data"]
            symbol: str = channel.replace("instrument_info.100ms.", "")
            tick: TickData = self.ticks[symbol]
            if type_ == "snapshot":
                if not data["last_price"]:  # 过滤最新价为0的数据
                    return

                tick.trade_price = float(data["last_price"])
                tick.trade_volume = int(data["volume_24h_e8"]) / 100000000
                tick.datetime = generate_datetime(data["updated_at"])

            else:
                update: dict = data["update"][0]

                if "last_price" not in update:  # 过滤最新价为0的数据
                    return

                tick.trade_price = float(update["last_price"])
                if update["volume_24h_e8"]:
                    tick.trade_volume = int(update["volume_24h_e8"]) / 100000000
                tick.datetime = generate_datetime(update["updated_at"])

            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))

        if "orderBookL2_25" in channel:
            # tick_5
            type_: str = packet["type"]
            data: dict = packet["data"]
            if not data:
                return

            symbol: str = channel.replace("orderBookL2_25.", "")
            tick: TickData = self.ticks[symbol]
            bids: dict = self.symbol_bids.setdefault(symbol, {})
            asks: dict = self.symbol_asks.setdefault(symbol, {})

            if type_ == "snapshot":

                buf: list = data["order_book"]

                for d in buf:
                    price: float = float(d["price"])

                    if d["side"] == "Buy":
                        bids[price] = d
                    else:
                        asks[price] = d
            else:
                for d in data["delete"]:
                    price: float = float(d["price"])

                    if d["side"] == "Buy":
                        bids.pop(price)
                    else:
                        asks.pop(price)

                for d in (data["update"] + data["insert"]):

                    price: float = float(d["price"])
                    if d["side"] == "Buy":
                        bids[price] = d
                    else:
                        asks[price] = d

            bid_keys: list = list(bids.keys())
            bid_keys.sort(reverse=True)

            ask_keys: list = list(asks.keys())
            ask_keys.sort()

            for i in range(5):
                n = i + 1

                bid_price = bid_keys[i]
                bid_data = bids[bid_price]
                ask_price = ask_keys[i]
                ask_data = asks[ask_price]

                setattr(tick, f"bid_price_{n}", bid_price)
                setattr(tick, f"bid_volume_{n}", bid_data["size"])
                setattr(tick, f"ask_price_{n}", ask_price)
                setattr(tick, f"ask_volume_{n}", ask_data["size"])

            tick.datetime = generate_datetime_2(int(packet["timestamp_e6"]) / 1000000)
            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))

        if "trade" in channel:
            # transaction
            symbol: str = channel.replace("trade.", "")
            l = packet["data"]
            for data in l:
                transaction: TradeData = self.transactions[symbol]

                transaction.datetime = generate_datetime_2(int(data["trade_time_ms"]) / 1000)
                transaction.volume = data["size"]
                transaction.price = data["price"]
                transaction.direction = Direction.SHORT if data["side"] == "Sell" else Direction.LONG

                self.gateway.on_transaction(copy(transaction))

        if "orderBook_200" in channel:
            # depth
            symbol: str = channel.replace("orderBook_200.100ms.", "")
            type_: str = packet["type"]
            data: dict = packet["data"]
            depth: DepthData = self.depths[symbol]
            depth.localtime = datetime.now()
            if not data:
                return

            depth.datetime = generate_datetime_2(int(packet["timestamp_e6"]) / 1000000)
            if type_ == "snapshot":
                buf = data["order_book"]
                for d in buf:
                    depth.price = d["price"]
                    depth.volume = d["size"]
                    depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                    self.gateway.on_depth(copy(depth))
            else:
                for key, buf in data.items():
                    if key == "delete":
                        for d in buf:
                            depth.price = float(d["price"])
                            depth.volume = 0
                            depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                            self.gateway.on_depth(copy(depth))

                    if key == "update" or key == "insert":
                        for d in buf:
                            depth.price = float(d["price"])
                            depth.volume = d["size"]
                            depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                            self.gateway.on_depth(copy(depth))


class BybitUBCTradeWebsocketListener(WebsocketListener):
    """u本位 合约的交易Websocket接口"""

    def __init__(self, gateway: Gateway) -> None:
        """构造函数"""
        super(BybitUBCTradeWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 30

        self.key: str = ""
        self.secret: bytes = b""
        self.server: str = ""

        self.callbacks: Dict[str, Callable] = {}
        self.ticks: Dict[str, TickData] = {}
        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.symbol_bids: Dict[str, dict] = {}
        self.symbol_asks: Dict[str, dict] = {}

    def connect(
            self,
            key: str,
            secret: str,
            server: str,
            proxy_host: str,
            proxy_port: int
    ) -> None:
        """连接Websocket私有频道"""
        self.key = key
        self.secret = secret.encode()
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.server = server

        if self.server == "REAL":
            url = PRIVATE_WEBSOCKET_HOST
        else:
            url = TESTNET_PRIVATE_WEBSOCKET_HOST

        self.init(url, self.proxy_host, self.proxy_port)
        self.start()

    def login(self) -> None:
        """用户登录"""
        expires: int = generate_timestamp(30)
        msg = f"GET/realtime{int(expires)}"
        signature: str = sign(self.secret, msg.encode())

        req: dict = {
            "op": "auth",
            "args": [self.key, expires, signature]
        }
        self.send_packet(req)

    def subscribe_topic(
            self,
            topic: str,
            callback: Callable[[str, dict], Any]
    ) -> None:
        """订阅私有频道"""
        self.callbacks[topic] = callback

        req: dict = {
            "op": "subscribe",
            "args": [topic],
        }
        self.send_packet(req)

    def on_connected(self) -> None:
        """连接成功回报"""
        self.gateway.write_log("交易Websocket API连接成功")
        self.login()

    def on_disconnected(self) -> None:
        """连接断开回报"""
        self.gateway.write_log("交易Websocket API连接断开")

    def on_packet(self, packet: dict) -> None:
        """推送数据回报"""
        if "topic" not in packet:
            op: str = packet["request"]["op"]
            if op == "auth":
                self.on_login(packet)
        else:
            channel: str = packet["topic"]
            callback: callable = self.callbacks[channel]
            callback(packet)
            self.gateway.on_raw(packet)


    def on_login(self, packet: dict):
        """用户登录请求回报"""
        success: bool = packet.get("success", False)
        if success:

            self.subscribe_topic("order", self.on_order)
            self.subscribe_topic("execution", self.on_trade)
            self.subscribe_topic("position", self.on_position)
            self.subscribe_topic("wallet", self.on_account)

        else:
            self.gateway.write_log("交易Websocket API登录失败")

    def on_account(self, packet: dict) -> None:
        """资金更新推送"""
        for d in packet["data"]:
            account = AccountData(
                accountid="USDT",
                balance=d["wallet_balance"],
                frozen=d["wallet_balance"] - d["available_balance"],
                gateway_name=self.gateway_name,
            )
            self.gateway.on_account(account)

    def on_trade(self, packet: dict) -> None:
        """成交更新推送"""
        for d in packet["data"]:
            orderid: str = d["order_link_id"]
            if not orderid:
                orderid: str = d["order_id"]

            trade: TradeData = TradeData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                orderid=orderid,
                tradeid=d["exec_id"],
                direction=DIRECTION_BYBIT2AB[d["side"]],
                price=float(d["price"]),
                volume=d["exec_qty"],
                datetime=generate_datetime(d["trade_time"]),
                gateway_name=self.gateway_name,
            )

            self.gateway.on_trade(trade)

    def on_order(self, packet: dict) -> None:
        """委托更新推送"""
        for d in packet["data"]:
            orderid: str = d["order_link_id"]
            if orderid:
                local_orderids.add(orderid)
            else:
                orderid: str = d["order_id"]

            dt: datetime = generate_datetime(d["create_time"])

            order: OrderData = OrderData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                orderid=orderid,
                type=ORDER_TYPE_BYBIT2AB[d["order_type"]],
                direction=DIRECTION_BYBIT2AB[d["side"]],
                price=float(d["price"]),
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

    def on_position(self, packet: dict) -> None:
        """持仓更新推送"""
        for d in packet["data"]:
            position: PositionData = PositionData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                direction=Direction.NET if d["mode"] == "MergedSingle" else DIRECTION_BYBIT2AB[d["side"]],
                volume=d["size"] if d["side"] == "Buy" else -d["size"],
                price=float(d["entry_price"]),
                gateway_name=self.gateway_name
            )
            self.gateway.on_position(position)


class BybitBBCMarketWebsocketListener(WebsocketListener):
    """币本位合约行情Websocket接口"""

    def __init__(self, gateway: Gateway):
        super(BybitBBCMarketWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 30

        self.ticks: Dict[str, TickData] = {}
        self.transactions: Dict[str, TransactionData] = {}
        self.depths: Dict[str, DepthData] = {}

        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.symbol_bids: Dict[str, dict] = {}
        self.symbol_asks: Dict[str, dict] = {}

    def connect(self, server: str, proxy_host: str, proxy_port: int) -> None:
        """ws行情"""

        self.server = server

        if self.server == "REAL":
            url = INVERSE_WEBSOCKET_HOST
        else:
            url = TESTNET_INVERSE_WEBSOCKET_HOST

        self.init(url, proxy_host, proxy_port)

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接成功")

        for req in list(self.subscribed.values()):
            self.subscribe(req)

    def on_disconnected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接断开")

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""

        # if req.symbol not in ubc_symbol_contract_map and req.symbol not in future_symbol_contract_map:
        #     self.gateway.write_log(f"找不到该合约代码{req.symbol}")
        #     return
        # 缓存订阅记录
        self.subscribed[req.symbol] = req

        symbol = req.symbol

        tick, depth, transaction, _ = self.make_data(symbol, Exchange.BYBIT, datetime.now(), self.gateway_name)
        self.ticks[symbol] = tick
        self.transactions[symbol] = transaction
        self.depths[symbol] = depth

        # 发送订阅请求
        subscribe_mode = self.gateway.subscribe_mode
        channels = []
        if subscribe_mode.best_tick:
            channels.append(f"instrument_info.100ms.{symbol}")
        if subscribe_mode.tick_5:
            channels.append(f"orderBookL2_25.{symbol}")
        if subscribe_mode.transaction:
            channels.append(f"trade.{symbol}")
        if subscribe_mode.depth:
            channels.append(f"orderBook_200.100ms.{symbol}")

        req_dict: dict = {
            "op": "subscribe",
            "args": channels
        }

        self.send_packet(req_dict)

    def on_packet(self, packet: dict):

        if "topic" not in packet:
            return
        channel: str = packet["topic"]

        if "instrument_info" in channel:
            # best_tick
            type_: str = packet["type"]
            data: dict = packet["data"]
            symbol: str = channel.replace("instrument_info.100ms.", "")
            tick: TickData = self.ticks[symbol]
            if type_ == "snapshot":
                if not data["last_price"]:  # 过滤最新价为0的数据
                    return

                tick.trade_price = float(data["last_price"])

                tick.trade_volume = data["volume_24h"]

                update_time: str = data.get("updated_at", None)
                if update_time:
                    tick.datetime = generate_datetime(data["updated_at"])
                else:
                    tick.datetime = generate_datetime_2(data["updated_at_e9"] / 1000000000)
            else:
                update: dict = data["update"][0]

                if "last_price" not in update:  # 过滤最新价为0的数据
                    return

                tick.trade_price = float(update["last_price"])

                tick.trade_volume = update["volume_24h"]

                update_time: str = update.get("updated_at", None)
                if update_time:
                    tick.datetime = generate_datetime(update["updated_at"])
                else:
                    tick.datetime = generate_datetime_2(packet["timestamp_e6"] / 1000000)

            self.gateway.on_tick(copy(tick))

        if "orderBookL2_25" in channel:
            # tick_5
            type_: str = packet["type"]
            data: dict = packet["data"]
            if not data:
                return

            symbol: str = channel.replace("orderBookL2_25.", "")
            tick: TickData = self.ticks[symbol]
            bids: dict = self.symbol_bids.setdefault(symbol, {})
            asks: dict = self.symbol_asks.setdefault(symbol, {})

            if type_ == "snapshot":

                for d in data:
                    price: float = float(d["price"])

                    if d["side"] == "Buy":
                        bids[price] = d
                    else:
                        asks[price] = d
            else:
                for d in data["delete"]:
                    price: float = float(d["price"])

                    if d["side"] == "Buy":
                        bids.pop(price)
                    else:
                        asks.pop(price)

                for d in (data["update"] + data["insert"]):

                    price: float = float(d["price"])
                    if d["side"] == "Buy":
                        bids[price] = d
                    else:
                        asks[price] = d

            bid_keys: list = list(bids.keys())
            bid_keys.sort(reverse=True)

            ask_keys: list = list(asks.keys())
            ask_keys.sort()

            for i in range(5):
                n = i + 1

                bid_price = bid_keys[i]
                bid_data = bids[bid_price]
                ask_price = ask_keys[i]
                ask_data = asks[ask_price]

                setattr(tick, f"bid_price_{n}", bid_price)
                setattr(tick, f"bid_volume_{n}", bid_data["size"])
                setattr(tick, f"ask_price_{n}", ask_price)
                setattr(tick, f"ask_volume_{n}", ask_data["size"])

            tick.datetime = generate_datetime_2(int(packet["timestamp_e6"]) / 1000000)
            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))

        if "trade" in channel:
            # transaction
            symbol: str = channel.replace("trade.", "")
            l = packet["data"]
            for data in l:
                transaction: TradeData = self.transactions[symbol]

                transaction.datetime = generate_datetime_2(int(data["trade_time_ms"]) / 1000)
                transaction.volume = data["size"]
                transaction.price = data["price"]
                transaction.direction = Direction.SHORT if data["side"] == "Sell" else Direction.LONG

                self.gateway.on_transaction(copy(transaction))

        if "orderBook_200" in channel:
            # depth
            symbol: str = channel.replace("orderBook_200.100ms.", "")
            type_: str = packet["type"]
            data: dict = packet["data"]
            depth: DepthData = self.depths[symbol]
            depth.localtime = datetime.now()
            if not data:
                return

            depth.datetime = generate_datetime_2(int(packet["timestamp_e6"]) / 1000000)
            if type_ == "snapshot":
                for d in data:
                    depth.price = d["price"]
                    depth.volume = d["size"]
                    depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                    self.gateway.on_depth(copy(depth))
            else:
                for key, buf in data.items():
                    if key == "delete":
                        for d in buf:
                            depth.price = float(d["price"])
                            depth.volume = 0
                            depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                            self.gateway.on_depth(copy(depth))

                    if key == "update" or key == "insert":
                        for d in buf:
                            depth.price = float(d["price"])
                            depth.volume = d["size"]
                            depth.direction = Direction.SHORT if d["side"] == "Sell" else Direction.LONG
                            self.gateway.on_depth(copy(depth))


class BybitBBCTradeWebsocketListener(WebsocketListener):
    """币本位合约交易websocket接口"""

    def __init__(self, gateway: Gateway) -> None:
        """构造函数"""
        super(BybitBBCTradeWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 30

        self.key: str = ""
        self.secret: bytes = b""
        self.server: str = ""

        self.callbacks: Dict[str, Callable] = {}
        self.ticks: Dict[str, TickData] = {}
        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.symbol_bids: Dict[str, dict] = {}
        self.symbol_asks: Dict[str, dict] = {}

    def connect(
            self,
            key: str,
            secret: str,
            server: str,
            proxy_host: str,
            proxy_port: int
    ) -> None:
        """连接Websocket私有频道"""
        self.key = key
        self.secret = secret.encode()
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.server = server

        if self.server == "REAL":
            url = INVERSE_WEBSOCKET_HOST
        else:
            url = TESTNET_INVERSE_WEBSOCKET_HOST

        self.init(url, self.proxy_host, self.proxy_port)
        self.start()

    def login(self) -> None:
        """用户登录"""
        expires: int = generate_timestamp(30)
        msg = f"GET/realtime{int(expires)}"
        signature: str = sign(self.secret, msg.encode())

        req: dict = {
            "op": "auth",
            "args": [self.key, expires, signature]
        }
        self.send_packet(req)

    def subscribe_topic(
            self,
            topic: str,
            callback: Callable[[str, dict], Any]
    ) -> None:
        """订阅私有频道"""
        self.callbacks[topic] = callback

        req: dict = {
            "op": "subscribe",
            "args": [topic],
        }
        self.send_packet(req)

    def on_connected(self) -> None:
        """连接成功回报"""
        self.gateway.write_log("交易Websocket API连接成功")
        self.login()

    def on_disconnected(self) -> None:
        """连接断开回报"""
        self.gateway.write_log("交易Websocket API连接断开")

    def on_packet(self, packet: dict) -> None:
        """推送数据回报"""
        if "topic" not in packet:
            op: str = packet["request"]["op"]
            if op == "auth":
                self.on_login(packet)
        else:
            channel: str = packet["topic"]
            callback: callable = self.callbacks[channel]
            callback(packet)
            self.gateway.on_raw(packet)

    def on_login(self, packet: dict):
        """用户登录请求回报"""
        success: bool = packet.get("success", False)
        if success:

            self.subscribe_topic("order", self.on_order)
            self.subscribe_topic("execution", self.on_trade)
            self.subscribe_topic("position", self.on_position)

        else:
            self.gateway.write_log("交易Websocket API登录失败")

    def on_trade(self, packet: dict) -> None:
        """成交更新推送"""
        for d in packet["data"]:
            orderid: str = d["order_link_id"]
            if not orderid:
                orderid: str = d["order_id"]

            trade: TradeData = TradeData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                orderid=orderid,
                tradeid=d["exec_id"],
                direction=DIRECTION_BYBIT2AB[d["side"]],
                price=float(d["price"]),
                volume=d["exec_qty"],
                datetime=generate_datetime(d["trade_time"]),
                gateway_name=self.gateway_name,
            )

            self.gateway.on_trade(trade)

    def on_order(self, packet: dict) -> None:
        """委托更新推送"""
        for d in packet["data"]:
            orderid: str = d["order_link_id"]
            if orderid:
                local_orderids.add(orderid)
            else:
                orderid: str = d["order_id"]

            dt: datetime = generate_datetime(d["timestamp"])

            order: OrderData = OrderData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                orderid=orderid,
                type=ORDER_TYPE_BYBIT2AB[d["order_type"]],
                direction=DIRECTION_BYBIT2AB[d["side"]],
                price=float(d["price"]),
                volume=d["qty"],
                traded=d["cum_exec_qty"],
                status=STATUS_BYBIT2AB[d["order_status"]],
                datetime=dt,
                gateway_name=self.gateway_name
            )

            self.gateway.on_order(order)

    def on_position(self, packet: dict) -> None:
        """持仓更新推送"""
        for d in packet["data"]:
            if d["side"] == "Buy":
                volume = d["size"]
            else:
                volume = -d["size"]

            position: PositionData = PositionData(
                symbol=d["symbol"],
                exchange=Exchange.BYBIT,
                direction=Direction.NET,
                volume=volume,
                price=float(d["entry_price"]),
                gateway_name=self.gateway_name
            )
            self.gateway.on_position(position)

            balance: float = get_float_value(d, "wallet_balance")
            frozen: float = balance - get_float_value(d, "available_balance")
            account: AccountData = AccountData(
                accountid=d["symbol"].split("USD")[0],
                balance=balance,
                frozen=frozen,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_account(account)
