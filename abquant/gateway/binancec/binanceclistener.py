

from logging import WARNING
from abquant.gateway import accessor
from abquant.trader.utility import round_to
from datetime import datetime
from typing import Dict, List, Optional
from copy import copy, deepcopy

from . import DIRECTION_BINANCEC2AB, D_TESTNET_WEBSOCKET_DATA_HOST, D_WEBSOCKET_DATA_HOST, F_TESTNET_WEBSOCKET_DATA_HOST, F_WEBSOCKET_DATA_HOST, ORDERTYPE_BINANCEC2AB, STATUS_BINANCEC2AB, symbol_contract_map
from ..basegateway import Gateway
from ..listener import WebsocketListener
from abquant.trader.exception import MarketException
from abquant.trader.common import Direction, Exchange
from abquant.trader.object import AccountData, PositionData, SubscribeRequest
from abquant.trader.msg import DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData


class BinanceCDataWebsocketListener(WebsocketListener):
    """"""

    def __init__(self, gateway: Gateway):
        """"""
        super(BinanceCDataWebsocketListener, self).__init__(gateway)

        self.ticks: Dict[str, TickData] = {}
        self.transactions: Dict[str, TransactionData] = {}
        self.depths: Dict[str, DepthData] = {}
        self.entrusts: Dict[str, EntrustData] = {}
        self.usdt_base = False

    def connect(
        self,
        usdt_base: bool,
        proxy_host: str,
        proxy_port: int,
        server: str
    ) -> None:
        """"""
        self.usdt_base = usdt_base
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.server = server

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接")

    def on_disconnected(self):
        """"""
        self.gateway.write_log("行情Websocket API连接断开")

    def subscribe(self, req: SubscribeRequest) -> None:
        #TODO symbol_contract_map 分 BBC UBC
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

        if self.server == "REAL":
            url = F_WEBSOCKET_DATA_HOST + "/".join(channels)
            if not self.usdt_base:
                url = D_WEBSOCKET_DATA_HOST + "/".join(channels)
        else:
            url = F_TESTNET_WEBSOCKET_DATA_HOST + "/".join(channels)
            if not self.usdt_base:
                url = D_TESTNET_WEBSOCKET_DATA_HOST + "/".join(channels)

        self.init(url, self.proxy_host, self.proxy_port, ping_interval=10)

        # self.start()

    def on_packet(self, packet: dict) -> None:
        """"""

        stream = packet["stream"]
        data = packet["data"]

        index = stream.find("@")
        channel = stream[index+1:]
        symbol = stream[:index]

        newest = datetime.fromtimestamp(float(data['T']) / 1000)

        if channel == "bookTicker":

            tick = self.ticks[symbol]
            if newest < tick.datetime:
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
            if newest < transaction.datetime:
                return 
            transaction.datetime = newest
            transaction.volume = float(data['q'])
            transaction.price = float(data['p'])
            transaction.direction = Direction.SHORT if data['m'] else Direction.LONG
            transaction.times = int(data['l']) - int(data['f'])
            transaction.localtime = datetime.now()

            self.gateway.on_transaction(copy(transaction))

            tick = self.ticks[symbol]
            if tick.datetime < newest:
                tick.datetime = newest
            tick.trade_price = float(data['p'])
            tick.trade_volume = float(data['q'])
            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))

        elif channel == 'depth@100ms':
            depth = self.depths[symbol]
            depth.localtime = datetime.now()
            if newest < depth.datetime:
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
            bids = data["b"]

            # clear transaction inforamtion
            tick.trade_price = 0
            tick.trade_volume = 0
            for n in range(min(5, len(bids))):
                price, volume = bids[n]
                tick.__setattr__("bid_price_" + str(n + 1), float(price))
                tick.__setattr__("bid_volume_" + str(n + 1), float(volume))

            asks = data["a"]
            for n in range(min(5, len(asks))):
                price, volume = asks[n]
                tick.__setattr__("ask_price_" + str(n + 1), float(price))
                tick.__setattr__("ask_volume_" + str(n + 1), float(volume))
            # tick time checkout to update best ask/bid
            if tick.datetime < newest:
                tick.datetime = newest
                tick.best_ask_price = tick.ask_price_1
                tick.best_ask_volume = tick.ask_volume_1
                tick.best_bid_price = tick.bid_price_1
                tick.best_bid_volume = tick.bid_volume_1
            tick.localtime = datetime.now()
            self.gateway.on_tick(copy(tick))
        else: 
            raise MarketException("Unrecognized channel from {}: packet content, \n{}".format(self.gateway_name, packet))
    

class BinanceCTradeWebsocketListener(WebsocketListener):
    """"""

    def __init__(self, gateway: Gateway):
        """"""
        super(BinanceCTradeWebsocketListener, self).__init__(gateway)

        # TODO for now it is not implemented and no-use at all. property below is for self-contained reason, will be implemented in the future.
        self.accounts = {}
        self.orders = {}
        self.positions = {}


    def connect(self, url: str, proxy_host: str, proxy_port: int) -> None:
        """"""
        self.init(url, proxy_host, proxy_port, ping_interval=10)
        self.start()

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("交易Websocket API连接成功")
    
    def on_disconnected(self):
        self.gateway.write_log("交易Websocket API断开")

    def on_packet(self, packet: dict) -> None:  
        """"""
        if packet["e"] == "ACCOUNT_UPDATE":
            self.on_account(packet)
        elif packet["e"] == "ORDER_TRADE_UPDATE":
            self.on_order(packet)

    def on_account(self, packet: dict) -> None:
        """"""
        for acc_data in packet["a"]["B"]:
            account = AccountData(
                accountid=acc_data["a"],
                balance=float(acc_data["wb"]),
                frozen=float(acc_data["wb"]) - float(acc_data["cw"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)
        
        for pos_data in packet["a"]["P"]:
            if pos_data["ps"] == "BOTH":
                volume = pos_data["pa"]
                if '.' in volume:
                    volume = float(volume)
                else:
                    volume = int(volume)

                position = PositionData(
                    symbol=pos_data["s"],
                    exchange=Exchange.BINANCE,
                    direction=Direction.NET,
                    volume=volume,
                    price=float(pos_data["ep"]),
                    pnl=float(pos_data["cr"]),
                    gateway_name=self.gateway_name,
                )
                self.gateway.on_position(position)

    def on_order(self, packet: dict) -> None:
        """"""

        ord_data = packet["o"]
        key = (ord_data["o"], ord_data["f"])
        order_type = ORDERTYPE_BINANCEC2AB.get(key, None)
        if not order_type:
            return

        order = OrderData(
            symbol=ord_data["s"],
            exchange=Exchange.BINANCE,
            orderid=str(ord_data["c"]),
            type=order_type,
            direction=DIRECTION_BINANCEC2AB[ord_data["S"]],
            price=float(ord_data["p"]),
            volume=float(ord_data["q"]),
            traded=float(ord_data["z"]),
            status=STATUS_BINANCEC2AB[ord_data["X"]],
            datetime=datetime.fromtimestamp(packet["E"] / 1000),
            gateway_name=self.gateway_name
        )

        self.gateway.on_order(order)

        # Round trade volume to minimum trading volume
        trade_volume = float(ord_data["l"])

        contract = symbol_contract_map.get(order.symbol, None)
        if contract:
            trade_volume = round_to(trade_volume, contract.size)

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
