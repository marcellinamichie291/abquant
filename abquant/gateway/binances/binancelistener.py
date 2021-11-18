
from logging import WARNING
from abquant.gateway import accessor
from abquant.trader.utility import round_to
from datetime import datetime
from typing import Dict, List, Optional
from copy import copy, deepcopy

from abquant.gateway.binances import DIRECTION_BINANCE2AB,WEBSOCKET_TRADE_HOST, WEBSOCKET_DATA_HOST, ORDERTYPE_BINANCE2AB, STATUS_BINANCE2AB, symbol_contract_map
from ..basegateway import Gateway
from ..listener import WebsocketListener
from abquant.trader.exception import MarketException
from abquant.trader.common import Direction, Exchange
from abquant.trader.object import AccountData, PositionData, SubscribeRequest
from abquant.trader.msg import DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData, Status


class BinanceSDataWebsocketListener(WebsocketListener):
    """"""

    def __init__(self, gateway: Gateway):
        """"""
        super(BinanceSDataWebsocketListener, self).__init__(gateway)

        self.ticks: Dict[str, TickData] = {}
        self.transactions: Dict[str, TransactionData] = {}
        self.depths: Dict[str, DepthData] = {}
        self.entrusts: Dict[str, EntrustData] = {}

    def connect(
            self,
            proxy_host: str,
            proxy_port: int
    ) -> None:
        """"""
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接")

    def on_disconnected(self):
        """"""
        self.gateway.write_log("行情Websocket API连接断开")

    def start(self):
        super(BinanceSDataWebsocketListener, self).start()

    def subscribe(self, req: SubscribeRequest) -> None:
        # TODO symbol_contract_map 分 BBC UBC
        if req.symbol not in symbol_contract_map:
            self.gateway.write_log(f"找不到该合约代码{req.symbol}", level=WARNING)
            return
        tick, depth, transaction, entrust = self.make_data(req.symbol, Exchange.BINANCE, datetime.now(), self.gateway_name)

        symbol = req.symbol.lower()
        self.ticks[symbol] = tick
        self.transactions[symbol] = transaction
        self.depths[symbol] = depth
        self.entrusts[symbol] = entrust

        # Close previous connection
        if self._active:
            self.stop()
            self.join()

        # Create new connection
        channels = []
        for ws_symbol in self.ticks.keys():
            subscribe_mode = self.gateway.subscribe_mode
            if subscribe_mode.best_tick:
                channels.append(ws_symbol + "@bookTicker")
            if subscribe_mode.tick_5:
                channels.append(ws_symbol + "@depth5@100ms")
            if subscribe_mode.transaction:
                channels.append(ws_symbol + "@aggTrade")
            if subscribe_mode.depth:
                # todoDone diff depth update, not supported yet because the "e" field of payload of chanel "Partial Book Depth Streams" and "Diff. Book Depth Streams" standing for event/channel type are both "depthUpdate"
                channels.append(ws_symbol + "@depth@100ms")

        url = WEBSOCKET_DATA_HOST + "/".join(channels)

        self.init(url, self.proxy_host, self.proxy_port, ping_interval=10)

        # self.start()

    def on_packet(self, packet: dict) -> None:
        """"""

        stream = packet["stream"]
        data = packet["data"]

        index = stream.find("@")
        channel = stream[index + 1:]
        symbol = stream[:index]

        newest = None
        if 'T' in data:
            newest = datetime.fromtimestamp(float(data['T']) / 1000)

        if channel == "bookTicker":

            tick = self.ticks[symbol]
            if newest is not None and newest < tick.datetime:
                return
            tick.datetime = newest

            # clear trade information
            tick.trade_price = 0
            tick.trade_volume = 0

            tick.best_ask_price = float(data['a'])
            tick.best_ask_volume = float(data['A'])
            tick.best_bid_price = float(data['b'])
            tick.best_bid_volume = float(data['B'])
            tick.localtime = datetime.now()

            self.gateway.on_tick(copy(tick))

        elif channel == 'aggTrade':
            transaction = self.transactions[symbol]
            # if newest < transaction.datetime:
            if newest is not None and newest < transaction.datetime:
                return

            transaction.datetime = newest
            transaction.volume = float(data['q'])
            transaction.price = float(data['p'])
            transaction.direction = Direction.SHORT if data['m'] else Direction.LONG
            transaction.times = int(data['l']) - int(data['f'])
            transaction.localtime = datetime.now()

            self.gateway.on_transaction(copy(transaction))

            tick = self.ticks[symbol]
            if newest is not None and newest.datetime < newest:
                tick.datetime = newest
            tick.trade_price = float(data['p'])
            tick.trade_volume = float(data['q'])
            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))

        elif channel == 'depth@100ms':
            depth = self.depths[symbol]
            depth.localtime = datetime.now()
            if newest is not None and newest < depth.datetime:
                return
            depth.datetime = newest
            for p, v in data['a']:
                depth.volume = float(v)
                depth.price = float(p)
                depth.direction = Direction.SHORT
                self.gateway.on_depth(copy(depth))

            for p, v in data['b']:
                depth.volume = float(v)
                depth.price = float(p)
                depth.direction = Direction.LONG
                self.gateway.on_depth(copy(depth))

        elif channel == 'depth5@100ms':
            tick = self.ticks[symbol]
            bids = data["bids"]

            # clear transaction inforamtion
            tick.trade_price = 0
            tick.trade_volume = 0
            for n in range(min(5, len(bids))):
                price, volume = bids[n]
                tick.__setattr__("bid_price_" + str(n + 1), float(price))
                tick.__setattr__("bid_volume_" + str(n + 1), float(volume))

            asks = data["asks"]
            for n in range(min(5, len(asks))):
                price, volume = asks[n]
                tick.__setattr__("ask_price_" + str(n + 1), float(price))
                tick.__setattr__("ask_volume_" + str(n + 1), float(volume))
            # tick time checkout to update best ask/bid
            if newest is not None and tick.datetime < newest:
                tick.datetime = newest
                tick.best_ask_price = tick.ask_price_1
                tick.best_ask_volume = tick.ask_volume_1
                tick.best_bid_price = tick.bid_price_1
                tick.best_bid_volume = tick.bid_volume_1
            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))
        else:
            raise MarketException \
                ("Unrecognized channel from {}: packet content, \n{}".format(self.gateway_name, packet))


class BinanceSTradeWebsocketListener(WebsocketListener):
    """"""

    def __init__(self, gateway: Gateway):
        """"""
        super().__init__(gateway)

        # TODO for now it is not implemented and no-use at all. property below is for self-contained reason, will be implemented in the future.
        self.accounts = {}
        self.orders = {}
        self.positions = {}

    def connect(self, url:str, proxy_host: str, proxy_port: int) -> None:
        """"""

        # url = WEBSOCKET_TRADE_HOST
        self.init(url, proxy_host, proxy_port, ping_interval=10)
        self.start()

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("交易Websocket API连接成功")

    def on_disconnected(self):
        self.gateway.write_log("交易Websocket API断开")

    def on_packet(self, packet: dict) -> None:
        """"""
        if packet["e"] == "outboundAccountPosition":
            self.on_account(packet)
        elif packet["e"] == "executionReport":
            self.on_order(packet)

    def on_account(self, packet: dict) -> None:
        """"""
        for acc_data in packet["B"]:
            account = AccountData(
                accountid=acc_data["a"],
                balance=float(acc_data["f"]) + float(acc_data["l"]),
                frozen=float(acc_data["l"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

    def on_order(self, packet: dict) -> None:
        print(packet)
        """
        NEW 新订单
        CANCELED 订单被取消
        REPLACED (保留字段，当前未使用)
        REJECTED 新订单被拒绝
        TRADE 订单有新成交
        EXPIRED 订单失效(根据订单的Time In Force参数)

        {
          "e": "executionReport",        // 事件类型
          "E": 1499405658658,            // 事件时间
          "s": "ETHBTC",                 // 交易对
          "c": "mUvoqJxFIILMdfAW5iGSOW", // clientOrderId
          "S": "BUY",                    // 订单方向
          "o": "LIMIT",                  // 订单类型
          "f": "GTC",                    // 有效方式
          "q": "1.00000000",             // 订单原始数量
          "p": "0.10264410",             // 订单原始价格
          "P": "0.00000000",             // 止盈止损单触发价格
          "F": "0.00000000",             // 冰山订单数量
          "g": -1,                       // OCO订单 OrderListId
          "C": "",                       // 原始订单自定义ID(原始订单，指撤单操作的对象。撤单本身被视为另一个订单)
          "x": "NEW",                    // 本次事件的具体执行类型
          "X": "NEW",                    // 订单的当前状态
          "r": "NONE",                   // 订单被拒绝的原因
          "i": 4293153,                  // orderId
          "l": "0.00000000",             // 订单末次成交量
          "z": "0.00000000",             // 订单累计已成交量
          "L": "0.00000000",             // 订单末次成交价格
          "n": "0",                      // 手续费数量
          "N": null,                     // 手续费资产类别
          "T": 1499405658657,            // 成交时间
          "t": -1,                       // 成交ID
          "I": 8641984,                  // 请忽略
          "w": true,                     // 订单是否在订单簿上？
          "m": false,                    // 该成交是作为挂单成交吗？
          "M": false,                    // 请忽略
          "O": 1499405658657,            // 订单创建时间
          "Z": "0.00000000",             // 订单累计已成交金额
          "Y": "0.00000000",              // 订单末次成交金额
          "Q": "0.00000000"              // Quote Order Qty
        }

        """

        ord_data = packet
        key = ord_data["o"]
        order_type = ORDERTYPE_BINANCE2AB.get(key, None)
        if not order_type:
            return

        status = None

        binance_spot_status = ord_data['X']

        if binance_spot_status == 'NEW':
            status = Status.NOTTRADED
        elif binance_spot_status == 'REJECTED':
            status = Status.REJECTED
        elif binance_spot_status == 'CANCELED':
            status = Status.CANCELLED
        elif binance_spot_status == 'EXPIRED':
            status = Status.CANCELLED
        elif binance_spot_status == 'TRADE':
            if float(ord_data['q']) == float(ord_data['z']):
                status = Status.ALLTRADED
            elif float(ord_data['z']) != 0:
                status = Status.PARTTRADED

        order = OrderData(
            symbol=ord_data["s"],
            exchange=Exchange.BINANCE,
            orderid=str(ord_data["c"]),
            type=order_type,
            direction=DIRECTION_BINANCE2AB[ord_data["S"]],
            price=float(ord_data["p"]),
            volume=float(ord_data["q"]),
            traded=float(ord_data["z"]),
            status=STATUS_BINANCE2AB[ord_data["X"]],
            datetime=datetime.fromtimestamp(ord_data["E"] / 1000),
            gateway_name=self.gateway_name
        )

        self.gateway.on_order(order)


        # Round trade volume to minimum trading volume
        trade_volume = float(ord_data["l"])

        contract = symbol_contract_map.get(order.symbol, None)
        if contract:
            trade_volume = round_to(trade_volume, contract.min_volume)

        if not trade_volume:
            return

        trade = TradeData(
            symbol=order.symbol,
            exchange=order.exchange,
            orderid=order.orderid,
            tradeid=ord_data["t"],
            direction=order.direction,
            price=float(ord_data["L"]),
            volume=trade_volume,
            datetime=datetime.fromtimestamp(ord_data["T"] / 1000),
            gateway_name=self.gateway_name,
        )
        self.gateway.on_trade(trade)
