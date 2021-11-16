
from logging import ERROR, WARNING
from re import T

from datetime import datetime
from typing import Dict, List, Optional
from copy import copy, deepcopy
import time
import hmac
import hashlib
import sys


from . import DIRECTION_AB2BITMEX, DIRECTION_BITMEX2AB, ORDERTYPE_BITMEX2AB, STATUS_BITMEX2AB, TESTNET_WEBSOCKET_HOST, WEBSOCKET_HOST, symbol_contract_map
from ..basegateway import Gateway
from ..listener import WebsocketListener
from abquant.trader.exception import MarketException
from abquant.trader.utility import round_to
from abquant.trader.common import Direction, Exchange, Product
from abquant.trader.object import AccountData, ContractData, PositionData, SubscribeRequest
from abquant.trader.msg import DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData


class BitmexListener(WebsocketListener):
    """"""

    def __init__(self, gateway: Gateway):
        """"""
        super(BitmexListener, self).__init__(gateway)

        self.key = ""
        self.secret = ""

        self.callbacks = {
            "trade": self.on_transaction,
            "orderBook10": self.on_depth5,
            "orderBookL2": self.on_depth,
            "execution": self.on_trade,
            "order": self.on_order,
            "position": self.on_position,
            "margin": self.on_account,
            # "quote": self.on_quote,
            "instrument": self.on_contract,
        }

        self.ticks: Dict[str, TickData] = {}
        self.transactions: Dict[str, TransactionData] = {}
        self.depths: Dict[str, DepthData] = {}
        self.id_depths_map: Dict[int, DepthData] = {}

        self.entrusts: Dict[str, EntrustData] = {}

        self.accounts: Dict[str, AccountData] = {}
        self.orders: Dict[str, OrderData] = {}
        self.positions: Dict[str, PositionData] = {}
        self.trades = set()

    def connect(
        self, key: str, secret: str, server: str, proxy_host: str, proxy_port: int
    ):
        """"""
        self.key = key
        self.secret = secret.encode()

        if server == "REAL":
            self.init(WEBSOCKET_HOST, proxy_host, proxy_port)
        else:
            self.init(TESTNET_WEBSOCKET_HOST, proxy_host, proxy_port)

    @staticmethod
    def parse_datatime(time_field: str):
        dt = datetime.strptime(time_field, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt

    def subscribe(self, req: SubscribeRequest):
        """
        Subscribe to tick data upate.
        """
        tick, depth, transaction, entrust = self.make_data(
            req.symbol, Exchange.BITMEX, None, self.gateway_name)
        symbol = req.symbol
        subscribe_mode = self.gateway.subscribe_mode
        if subscribe_mode.best_tick:
            self.ticks[symbol] = tick
        if subscribe_mode.tick_5:
            self.ticks[symbol] = tick
        if subscribe_mode.transaction:
            self.transactions[symbol] = transaction
            self.ticks[symbol] = tick
        if subscribe_mode.depth and symbol not in self.depths:
            self.depths[symbol] = depth
            # WARNING, when strategy need orderbook rebuilding, make sure what happen when reconnection.
            req = {
                "op": "subscribe",
                "args": [
                    "orderBookL2:{}".format(symbol),
                ],
            }
            self.send_packet(req)
        if subscribe_mode.entrust:
            self.entrusts[symbol] = entrust

    def on_connected(self):
        """"""
        self.gateway.write_log("Websocket API连接成功")
        self.authenticate()

    def on_disconnected(self):
        """"""
        self.gateway.write_log("Websocket API连接断开")

    def on_packet(self, packet: dict):
        """"""
        if "error" in packet:
            self.gateway.write_log("Websocket API报错：%s" %
                                   packet["error"], level=ERROR)

            if "not valid" in packet["error"]:
                self.stop()

        elif "request" in packet:
            req = packet["request"]
            success = packet["success"]

            if success:
                if req["op"] == "authKey":
                    self.gateway.write_log("Websocket API验证授权成功")
                    self.subscribe_topic()

        elif "table" in packet and packet["table"] == ('orderBookL2'):
            on_depth = self.callbacks['orderBookL2']
            action = packet["action"]
            if isinstance(packet["data"], list):
                for d in packet["data"]:
                    on_depth(d, action)
            else:
                on_depth(packet["data"], action)
        elif "table" in packet:
            name = packet["table"]
            callback = self.callbacks[name]

            if isinstance(packet["data"], list):
                for d in packet["data"]:
                    callback(d)
            else:
                callback(packet["data"])

    def authenticate(self):
        """
        Authenticate websockey connection to subscribe private topic.
        """
        expires = int(time.time())
        method = "GET"
        path = "/realtime"
        msg = method + path + str(expires)
        signature = hmac.new(
            self.secret, msg.encode(), digestmod=hashlib.sha256
        ).hexdigest()

        req = {"op": "authKey", "args": [self.key, expires, signature]}
        self.send_packet(req)

    def subscribe_topic(self):
        """
        Subscribe to all private topics.
        """
        req = {
            "op": "subscribe",
            "args": [
                "instrument",
                "trade",
                "orderBook10",
                # updated depth data is too much
                # "orderBookL2",
                # according to the test at 2021.10.15 ,quote is always been later than orderbook10.
                # "quote",
                "execution",
                "order",
                "position",
                "margin",
            ],
        }
        self.send_packet(req)
        self.gateway.write_log("账户资金查询")
        self.gateway.write_log("持仓信息查询")
        self.gateway.write_log("交易单信息查询")
        self.gateway.write_log("交易易所支持合约信息查询")

    def on_quote(self, d):
        symbol = d["symbol"]
        tick = self.ticks.get(symbol, None)
        parsed_datetime = self.parse_datatime(d["timestamp"])
        subscribe_mode = self.gateway.subscribe_mode
        if not tick or not subscribe_mode.best_tick:
            # print("it is late. {}".format(tick))
            return

        tick.trade_price = 0
        tick.trade_volume = 0
        tick.datetime = parsed_datetime
        tick.localtime = datetime.now()
        tick.best_bid_price = d['bidPrice']
        tick.best_bid_volume = d['bidSize']

        tick.best_ask_price = d['askPrice']
        tick.best_ask_volume = d['askSize']

    def on_transaction(self, d):
        """"""
        symbol = d["symbol"]
        tick = self.ticks.get(symbol, None)
        transaction = self.transactions.get(symbol, None)
        if not tick or not transaction:
            return

        # tick.last_price = d["price"]
        subscribe_mode = self.gateway.subscribe_mode

        local_time = datetime.now()
        parsed_datetime = self.parse_datatime(d["timestamp"])
        if tick and subscribe_mode.transaction:
            tick.trade_price = d["price"]
            tick.trade_volume = d["size"]
            tick.datetime = parsed_datetime
            tick.localtime = local_time
            self.gateway.on_tick(copy(tick))

        if transaction:
            transaction.localtime = local_time
            transaction.price = d["price"]
            transaction.volume = d["size"]
            transaction.times = 1
            transaction.datetime = parsed_datetime
            transaction.direction = DIRECTION_BITMEX2AB[d["side"]]
            self.gateway.on_transaction(copy(transaction))

    def on_depth5(self, d):
        """"""
        symbol = d["symbol"]
        tick = self.ticks.get(symbol, None)
        subscribe_mode = self.gateway.subscribe_mode
        if not tick:
            return
        if (not subscribe_mode.tick_5) and (not subscribe_mode.best_tick):
            return

        tick.trade_price = 0
        tick.trade_volume = 0
        tick.localtime = datetime.now()
        tick.datetime = self.parse_datatime(d['timestamp'])

        if subscribe_mode.best_tick:
            price, volume = d["bids"][0]
            tick.best_bid_volume = volume
            tick.best_bid_price = price

            price, volume = d["asks"][0]
            tick.best_ask_volume = volume
            tick.best_ask_price = price

        if subscribe_mode.tick_5:
            for n, buf in enumerate(d["bids"][:5]):
                price, volume = buf
                tick.__setattr__("bid_price_%s" % (n + 1), price)
                tick.__setattr__("bid_volume_%s" % (n + 1), volume)

            for n, buf in enumerate(d["asks"][:5]):
                price, volume = buf
                tick.__setattr__("ask_price_%s" % (n + 1), price)
                tick.__setattr__("ask_volume_%s" % (n + 1), volume)

        self.gateway.on_tick(copy(tick))

    def on_depth(self, d, action):
        symbol = d["symbol"]
        if symbol not in self.depths:
            return
        if action == 'partial' or action == 'insert':
            depth = self.id_depths_map.get(d['id'], None)
            if depth is not None:
                self.gateway.write_log(
                    msg="got a depth packet: {}. which should not exists in id_depth map".format(depth),
                    level=WARNING)
     
            depth = DepthData(gateway_name=self.gateway_name,
                              symbol=symbol,
                              exchange=Exchange.BITMEX,
                              datetime=None,
                              volume=d['size'],
                              price=d['price'],
                              direction=DIRECTION_BITMEX2AB[d['side']],
                              localtime=datetime.now()
                              )
            self.id_depths_map[d['id']] = depth
            self.depths[symbol] = depth

        elif action == 'update':
            depth = self.id_depths_map.get(d['id'], None)
            if depth is None:
                return
            depth.volume = d['size']
            depth.localtime = datetime.now()
            self.depths[symbol] = depth

        elif action == 'delete':
            depth = self.id_depths_map.get(d['id'], None)
            if depth is None:
                return
            self.id_depths_map.pop(d['id'])
            depth.volume = 0
            depth.localtime = datetime.now()
            self.depths[symbol] = depth
        else:
            raise MarketException(
                " there is problem with the 'action' field of orderBookL2 packet")
        self.gateway.on_depth(copy(depth))

    def on_trade(self, d):
        """"""
        # Filter trade update with no trade volume and side which is perpetual funding
        if not d["lastQty"] or not d["side"]:
            return

        tradeid = d["execID"]
        if tradeid in self.trades:
            return
        self.trades.add(tradeid)

        if d["clOrdID"]:
            orderid = d["clOrdID"]
        else:
            orderid = d["orderID"]

        trade = TradeData(
            symbol=d["symbol"],
            exchange=Exchange.BITMEX,
            orderid=orderid,
            tradeid=tradeid,
            direction=DIRECTION_BITMEX2AB[d["side"]],
            price=d["lastPx"],
            volume=d["lastQty"],
            datetime=self.parse_datatime(d["timestamp"]),
            gateway_name=self.gateway_name,
        )

        self.gateway.on_trade(trade)

    def on_order(self, d):
        """"""
        # Filter order data which cannot be processed properly
        if "ordStatus" not in d:
            return

        # Update local order data
        sysid = d["orderID"]
        order = self.orders.get(sysid, None)
        if not order:
            # Filter data with no trading side info
            side = d.get("side", "")
            if not side:
                return

            if d["clOrdID"]:
                orderid = d["clOrdID"]
            else:
                orderid = sysid

            order = OrderData(
                symbol=d["symbol"],
                exchange=Exchange.BITMEX,
                type=ORDERTYPE_BITMEX2AB.get([d["ordType"]], None),
                orderid=orderid,
                direction=DIRECTION_BITMEX2AB[side],
                price=d["price"],
                volume=d["orderQty"],
                datetime=self.parse_datatime(d["timestamp"]),
                gateway_name=self.gateway_name,
            )
            self.orders[sysid] = order

        order.traded = d.get("cumQty", order.traded)

        order.status = STATUS_BITMEX2AB.get(d["ordStatus"], order.status)

        self.gateway.on_order(copy(order))

    def on_position(self, d):
        """"""
        symbol = d["symbol"]

        position = self.positions.get(symbol, None)
        if not position:
            position = PositionData(
                symbol=d["symbol"],
                exchange=Exchange.BITMEX,
                direction=Direction.NET,
                gateway_name=self.gateway_name,
            )
            self.positions[symbol] = position

        volume = d.get("currentQty", None)
        if volume is not None:
            position.volume = volume

        price = d.get("avgEntryPrice", None)
        if price is not None:
            position.price = price

        self.gateway.on_position(copy(position))

    def on_account(self, d):
        """"""
        accountid = str(d["account"])
        account = self.accounts.get(accountid, None)
        if not account:
            account = AccountData(accountid=accountid,
                                  gateway_name=self.gateway_name)
            self.accounts[accountid] = account

        account.balance = d.get("marginBalance", account.balance)
        account.available = d.get("availableMargin", account.available)
        account.frozen = account.balance - account.available

        self.gateway.on_account(copy(account))

    def on_contract(self, d):
        """"""
        if "tickSize" not in d:
            return

        if not d["lotSize"]:
            return

        contract = ContractData(
            symbol=d["symbol"],
            exchange=Exchange.BITMEX,
            name=d["symbol"],
            product=Product.FUTURES,
            pricetick=d["tickSize"],
            size=d["lotSize"],
            stop_supported=True,
            net_position=True,
            history_data=True,
            on_board=self.parse_datatime(d['listing']),
            gateway_name=self.gateway_name,
        )
        symbol_contract_map[contract.symbol] = contract

        self.gateway.on_contract(contract)
