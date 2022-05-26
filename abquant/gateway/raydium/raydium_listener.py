from datetime import datetime
from typing import Dict
from copy import copy
from . import WEBSOCKET_HOST, raydium_symbols, pool_info, subscription_sid_map, sid_account_map, account_type_map, \
    account_symbol_map, symbol_liquidity_map, RaydiumLiquidityDate, new_subscribe_id, base64_decode, cal_output_amount
from .raydium_layout import AMM_INFO_LAYOUT_V4, OPEN_ORDERS_LAYOUT
from ..basegateway import Gateway
from ..listener import WebsocketListener
from abquant.trader.common import Exchange
from abquant.trader.object import SubscribeRequest
from abquant.trader.msg import TickData


class RaydiumWebsocketListener(WebsocketListener):

    def __init__(self, gateway: Gateway) -> None:
        """"""
        super(RaydiumWebsocketListener, self).__init__(gateway)

        self.gateway = gateway
        self.ping_interval = 10

        self.ticks: Dict[str, TickData] = {}

        self.subscribed: Dict[str, SubscribeRequest] = {}

        self.is_on_connected = False

    def connect(self) -> None:
        """连接Websocket交易频道"""
        self.init(WEBSOCKET_HOST)

    def on_connected(self) -> None:
        """连接成功回报"""
        self.is_on_connected = True
        self.gateway.write_log("Websocket 连接成功")

        for req in list(self.subscribed.values()):
            self.subscribe(req)

        msg = {"jsonrpc": "2.0", "id": 1, "method": "slotSubscribe"}
        self.send_packet(msg)

    def on_disconnected(self) -> None:
        """断开连接回报"""
        self.is_on_connected = False
        self.gateway.write_log("Websocket 连接断开")

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅"""
        symbol = req.symbol
        if symbol not in raydium_symbols:
            self.gateway.write_log(f"找不到该币对{req.symbol}")
            return

        self.subscribed[symbol] = req

        if not self.is_on_connected:
            return

        tick, _, _, _ = self.make_data(symbol, Exchange.RAYDIUNM, datetime.now(), self.gateway_name)
        self.ticks[symbol] = tick

        pool = pool_info(req.symbol)

        symbol_liquidity_map[symbol] = RaydiumLiquidityDate(base_decimals=pool['baseDecimals'],
                                                            quote_decimals=pool['quoteDecimals'])

        amm_id = pool['id']
        amm_base_vault = pool['baseVault']
        amm_quote_vault = pool['quoteVault']
        open_orders = pool['openOrders']

        account_type_map[amm_id] = 'id'
        account_type_map[amm_base_vault] = 'baseVault'
        account_type_map[amm_quote_vault] = 'quoteVault'
        account_type_map[open_orders] = 'openOrders'

        accounts = [amm_id, amm_base_vault, amm_quote_vault, open_orders]

        for account in accounts:
            sid = new_subscribe_id()
            sid_account_map[sid] = account
            account_symbol_map[account] = symbol

            msg = {"jsonrpc": "2.0", "id": sid, "method": "accountSubscribe",
                   "params": [account, {"encoding": "jsonParsed"}]}
            self.send_packet(msg)

    def on_packet(self, packet) -> None:
        """处理回传信息"""
        msg_json = packet

        if 'result' in msg_json.keys() and 'id' in msg_json.keys():
            """处理订阅成功信息，绑定subscription和id"""
            subscription = msg_json['result']
            sid = msg_json['id']
            subscription_sid_map[subscription] = sid

        elif 'method' in msg_json.keys() and msg_json['method'] == 'accountNotification':
            """处理订阅账户的回传数据"""
            subscription = msg_json['params']['subscription']
            sid = subscription_sid_map[subscription]
            account = sid_account_map[sid]
            account_type = account_type_map[account]
            symbol = account_symbol_map[account]
            liquidity_date = symbol_liquidity_map[symbol]

            if account_type == 'id':
                amm_id_data_base64 = msg_json['params']['result']['value']['data'][0]
                amm_id_data_decode = base64_decode(amm_id_data_base64, AMM_INFO_LAYOUT_V4)
                liquidity_date.base_need_take_pnl = amm_id_data_decode.baseNeedTakePnl
                liquidity_date.quote_need_take_pnl = amm_id_data_decode.quoteNeedTakePnl

            elif account_type == 'baseVault':
                tokenAmount = int(
                    msg_json['params']['result']['value']['data']['parsed']['info']['tokenAmount']['amount'])
                liquidity_date.base_vault_balance = tokenAmount

            elif account_type == 'quoteVault':
                tokenAmount = int(
                    msg_json['params']['result']['value']['data']['parsed']['info']['tokenAmount']['amount'])
                liquidity_date.quote_vault_balance = tokenAmount

            elif account_type == 'openOrders':
                open_order_data_base64 = msg_json['params']['result']['value']['data'][0]
                open_order_data_decode = base64_decode(open_order_data_base64, OPEN_ORDERS_LAYOUT)
                liquidity_date.open_order_base_token_amount = open_order_data_decode.base_token_total
                liquidity_date.open_order_quote_token_amount = open_order_data_decode.quote_token_total

        elif 'method' in msg_json.keys() and msg_json['method'] == 'slotNotification':
            for symbol in symbol_liquidity_map.keys():
                liquidity_date = symbol_liquidity_map[symbol]

                if liquidity_date.base_vault_balance > 0 and liquidity_date.quote_vault_balance > 0 and liquidity_date.base_need_take_pnl > 0 and liquidity_date.quote_need_take_pnl > 0 and liquidity_date.open_order_base_token_amount and liquidity_date.open_order_quote_token_amount > 0:
                    total_base = float(
                        liquidity_date.base_vault_balance + liquidity_date.open_order_base_token_amount - liquidity_date.base_need_take_pnl) / (
                                             10 ** liquidity_date.base_decimals)
                    total_quote = float(
                        liquidity_date.quote_vault_balance + liquidity_date.open_order_quote_token_amount - liquidity_date.quote_need_take_pnl) / (
                                              10 ** liquidity_date.quote_decimals)
                    best_ask_price = 0.0001 / (cal_output_amount(0.0001, total_quote, total_base))
                    best_bid_price = (cal_output_amount(0.0001, total_base, total_quote)) / 0.0001

                    tick = self.ticks[symbol]
                    tick.best_ask_price = best_ask_price
                    tick.best_bid_price = best_bid_price

                    self.gateway.on_tick(copy(tick))
