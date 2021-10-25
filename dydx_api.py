import argparse
from datetime import datetime, timedelta

import time
from abquant import event
from abquant import gateway 

from abquant.event import EventType, EventDispatcher, Event
from abquant.gateway import DydxGateway
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeMode, SubscribeRequest
from abquant.trader.common import Direction, Exchange, Interval, Offset, OrderType

dydx_setting = {
    "key": "",
    "secret": "",
    "passphrase": "",
    "stark_private_key": "",
    "proxy_host": "",
    "proxy_port": 0,
    "test_net": ["TESTNET", "REAL"][1],
    "limitFee": 0,
    "accountNumber": 0
}

event_dispatcher = EventDispatcher()
event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
    str('LOG: ') + str(event.data)))  # pass
# event_dispatcher.register(EventType.EVENT_TIMER, lambda event:  print(str('TIMER: ') + str(event.data))) #pass
event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(
    str('ACCOUNT: ') + str(event.data)))  # pass accessor,  trade_listerer not done
event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data))) # pass
event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(
    str('POSITION: ') + str(event.data)))  # pass accessor, trade_listerer not done
event_dispatcher.register(EventType.EVENT_EXCEPTION, lambda event: print(
    str('EXCEPTION: ') + str(event.data)))
event_dispatcher.register(EventType.EVENT_ORDER, lambda event: print(
    str('ORDER: ') + str(event.data)))
event_dispatcher.register(EventType.EVENT_TRADE, lambda event: print(
    str('TRADE: ') + str(event.data)))

dydx_gateway = DydxGateway(event_dispatcher)
dydx_gateway.connect(dydx_setting)

time.sleep(3)

dydx_gateway.set_subscribe_mode(SubscribeMode(
    transaction=True
))

dydx_gateway.subscribe(SubscribeRequest(
    symbol="BTC-USD", exchange=Exchange.DYDX
))

from abquant.gateway.dydx import symbol_contract_map

print(symbol_contract_map)

dydx_gateway.start()


