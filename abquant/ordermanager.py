from typing import Dict, Optional
from abquant.trader.msg import EntrustData, TickData, DepthData, TransactionData, OrderData, TradeData
from abquant.trader.object import PositionData, AccountData, ContractData
from abquant.event import Event
from abquant.event import EventType 
from abquant.event import EventDispatcher

class OrderManager:
    def __init__(self, event_dispatcher: EventDispatcher):
        """"""
        self.event_dispatcher = event_dispatcher

        self.ticks: Dict[str, TickData] = {}
        self.depths: Dict[str, DepthData] = {}
        self.entrusts: Dict[str, EntrustData] = {}
        self.transactions: Dict[str, TransactionData] = {}
        self.orders: Dict[str, OrderData] = {}
        self.trades: Dict[str, TradeData] = {}
        self.positions: Dict[str, PositionData] = {}
        self.accounts: Dict[str, AccountData] = {}
        self.contracts: Dict[str, ContractData] = {}

        self.active_orders: Dict[str, OrderData] = {}


    def register_event(self) -> None:
        """"""
        self.event_dispatcher.register(EventType.EVENT_TICK, self.process_tick_event)
        self.event_dispatcher.register(EventType.EVENT_DEPTH, self.process_depth_event)
        self.event_dispatcher.register(EventType.EVENT_TRANSACTION, self.process_transaction_event)
        self.event_dispatcher.register(EventType.EVENT_ENTRUST, self.process_entrust_event)
        self.event_dispatcher.register(EventType.EVENT_ORDER, self.process_order_event)
        self.event_dispatcher.register(EventType.EVENT_TRADE, self.process_trade_event)
        self.event_dispatcher.register(EventType.EVENT_POSITION, self.process_position_event)
        self.event_dispatcher.register(EventType.EVENT_ACCOUNT, self.process_account_event)
        self.event_dispatcher.register(EventType.EVENT_CONTRACT, self.process_contract_event)


    def process_tick_event(self, event: Event) -> None:
        """"""
        tick = event.data
        self.ticks[tick.ab_symbol] = tick

    def process_depth_event(self, event: Event) -> None:
        depth = event.data
        self.depths[depth.ab_symbol] = depth

    def process_transaction_event(self, event: Event) -> None:
        transaction = event.data
        self.transactions[transaction.ab_symbol] = transaction

    def process_entrust_event(self, event: Event) -> None:
        entrust = event.data
        self.entrusts[entrust.ab_symbol] = entrust

    def process_order_event(self, event: Event) -> None:
        """"""
        order = event.data
        self.orders[order.ab_orderid] = order

        # If order is active, then update data in dict.
        if order.is_active():
            self.active_orders[order.ab_orderid] = order
        # Otherwise, pop inactive order from in dict
        elif order.ab_orderid in self.active_orders:
            self.active_orders.pop(order.ab_orderid)

    def process_trade_event(self, event: Event) -> None:
        """"""
        trade = event.data
        self.trades[trade.ab_tradeid] = trade

    def process_position_event(self, event: Event) -> None:
        """"""
        position = event.data
        self.positions[position.ab_positionid] = position

    def process_account_event(self, event: Event) -> None:
        """"""
        account = event.data
        self.accounts[account.ab_accountid] = account

    def process_contract_event(self, event: Event) -> None:
        """"""
        contract = event.data
        self.contracts[contract.ab_symbol] = contract

    def get_tick(self, ab_symbol: str) -> Optional[TickData]:
        return self.ticks.get(ab_symbol, None)

    def get_depth(self, ab_symbol: str) -> Optional[DepthData]:
        return self.depths.get(ab_symbol, None)

    def get_transaction(self, ab_symbol: str) -> Optional[TransactionData]:
        return self.transactions.get(ab_symbol, None)
    
    def get_entrust(self, ab_symbol: str) -> Optional[EntrustData]:
        return self.entrusts.get(ab_symbol, None)
    

    def get_order(self, ab_orderid: str) -> Optional[OrderData]:
        return self.orders.get(ab_orderid, None)

    def get_trade(self, ab_tradeid: str) -> Optional[TradeData]:
        return self.trades.get(ab_tradeid, None)

    def get_position(self, ab_positionid: str) -> Optional[PositionData]:
        return self.positions.get(ab_positionid, None)

    def get_account(self, ab_accountid: str) -> Optional[AccountData]:
        return self.accounts.get(ab_accountid, None)

    def get_contract(self, ab_symbol: str) -> Optional[ContractData]:
        return self.contracts.get(ab_symbol, None)


    def get_all_active_orders(self, ab_symbol: str = "") -> List[OrderData]:
        """
        Get all active orders by ab_symbol.

        If ab_symbol is empty, return all active orders.
        """
        if not ab_symbol:
            return list(self.active_orders.values())
        else:
            active_orders = [
                order
                for order in self.active_orders.values()
                if order.ab_symbol == ab_symbol
            ]
            return active_orders

