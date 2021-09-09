import sys
from pathlib import Path
import time
import argparse

from abquant.event import EventDispatcher, EventType, Event
from abquant.gateway import BinanceBBCGateway, BinanceUBCGateway
from abquant.trader.object import CancelRequest, OrderRequest, SubscribeMode, SubscribeRequest
from abquant.trader.common import Direction, Exchange, Offset, OrderType

def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', type=str, required=True,
                        help='api key')
    parser.add_argument('-s', '--secret', type=str, required=True,
                        help='secret')
    parser.add_argument('-u', '--proxy_host', type=str,
                        # default='127.0.0.1',
                        help='proxy host')
    parser.add_argument('-p', '--proxy_port', type=int,
                        help='proxy port')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse()
    binance_setting = {
        "key": args.key,
        "secret": args.secret,
        "session_number": 3,
        "proxy_host": args.proxy_host if args.proxy_host else "",
        "proxy_port": args.proxy_port if args.proxy_port else 0,
        "test_net": ["TESTNET", "REAL"][1],
    }
    event_dispatcher = EventDispatcher()
    event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
        str('LOG: ') + str(event.data)))  # pass
    # event_dispatcher.register(EventType.EVENT_TIMER, lambda event:  print(str('TIMER: ') + str(event.data))) #pass
    event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(
        str('ACCOUNT: ') + str(event.data)))  # pass accessor,  trade_listerer not done
    # event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data))) # pass
    event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(
        str('POSITION: ') + str(event.data)))  # pass accessor, trade_listerer not done
    event_dispatcher.register(EventType.EVENT_EXCEPTION, lambda event: print(
        str('EXCEPTION: ') + str(event.data)))
    event_dispatcher.register(EventType.EVENT_ORDER, lambda event: print(
        str('ORDER: ') + str(event.data)))
    event_dispatcher.register(EventType.EVENT_TRADE, lambda event: print(
        str('TRADE: ') + str(event.data)))
    event_dispatcher.register(EventType.EVENT_TICK, lambda event: print(
        str('TICK: ') + str(event.data)))
    event_dispatcher.register(EventType.EVENT_DEPTH, lambda event: print(
        str('DEPTH: ') + str(event.data)))
    event_dispatcher.register(EventType.EVENT_TRANSACTION, lambda event: print(
        str('TRANSACTION: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_ENTRUST, lambda event:  print(str('ENTRUST: ') + str(event.data)))
    # event_dispatcher.register_general(lambda event: print(str(event.type) +  str(event.data)))
    gateway = BinanceUBCGateway(event_dispatcher)
    gateway.connect(binance_setting)

    time.sleep(3)

    from abquant.gateway.binancec import symbol_contract_map

    gateway.set_subscribe_mode(SubscribeMode(
        depth=False,
        tick_5=False,
        best_tick=False,
        entrust=False,
        transaction=True)
    )
    gateway.subscribe(SubscribeRequest(
        symbol='ICPUSDT', exchange=Exchange.BINANCE))
    for i, k in enumerate(symbol_contract_map):
        # if i > 0:
        #     break
        print(i, k)
        gateway.subscribe(SubscribeRequest(
            symbol=k, exchange=Exchange.BINANCE))

    # order_id: str = gateway.send_order(OrderRequest(symbol='XRPUSDT', exchange=Exchange.BINANCE, direction=Direction.SHORT, type=OrderType.LIMIT, volume=2, price=1.3, offset=Offset.OPEN))
    gateway.start()
    time.sleep(10)

    # gateway.cancel_order(CancelRequest(order_id.split('.')[-1], symbol='XRPUSDT', exchange=Exchange.BINANCE))
    while True:
        time.sleep(1)
