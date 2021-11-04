from datetime import datetime, timedelta

import time
from abquant import event
from abquant import gateway 

from abquant.event import EventType, EventDispatcher, Event
from abquant.gateway import DydxGateway, dydx
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeMode, SubscribeRequest
from abquant.trader.common import Direction, Exchange, Interval, Offset, OrderType



if __name__ == '__main__':

    dydx_setting = {
        "key": "0ec5b370-74d1-be64-a578-b7bb085ac937",
        "secret": "NLrG3Kuyspe0jt45gENM6UmWGLdSrwj88P-5UPrz",
        "passphrase": "rOkw33sCBiTQhE5PX_GR",
        "stark_private_key": "01a65d7c5fccd96786b0a42ba38df41f58383fcdace4be8581487b61739cc559",
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["TESTNET", "REAL"][1],
        "limitFee": 0.001, # makerFeeRate: 0.00050 or takerFeeRate: takerFeeRate: 0.00100
        "accountNumber": "0"
    }

    # dydx_setting = {
    #     "key": "0ec5b370-74d1-be64-a578-b7bb085ac937",
    #     "secret": "NLrG3Kuyspe0jt45gENM6UmWGLdSrwj88P-5UPrz",
    #     "passphrase": "rOkw33sCBiTQhE5PX_GR",
    #     "stark_private_key": "01a65d7c5fccd96786b0a42ba38df41f58383fcdace4be8581487b61739cc559",
    #     # "walletAddress":"0xf02f589bBaB91a8609D896aBeC1f8e4E5D1165c3",
    #     "proxy_host": "",
    #     "proxy_port": 0,
    #     "test_net": ["TESTNET", "REAL"][1],
    #     "limitFee": 0.001, # makerFeeRate: 0.00050 or takerFeeRate: takerFeeRate: 0.00100
    #     "accountNumber": 0
    # }

    event_dispatcher = EventDispatcher()

    # 根据事件类型 注册回调函数。 随意uncomment
    event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
        str('LOG: ') + str(event.data)))  # pass

    # event_dispatcher.register(EventType.EVENT_TIMER, lambda event:  print(str('TIMER: ') + str(event.data))) #pass

    # ok
    # event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(
    #     str('ACCOUNT: ') + str(event.data)))  # pass accessor,  trade_listerer not done

    # ok
    # event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data))) # pass

    # ok need test
    event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(
        str('POSITION: ') + str(event.data)))  # pass accessor, trade_listerer not done


    # event_dispatcher.register(EventType.EVENT_EXCEPTION, lambda event: print(
    #     str('EXCEPTION: ') + str(event.data)))

    # ok
    event_dispatcher.register(EventType.EVENT_ORDER, lambda event: print(
        str('ORDER: ') + str(event.data)))

    # need test
    event_dispatcher.register(EventType.EVENT_TRADE, lambda event: print(
        str('TRADE: ') + str(event.data)))

    # ok
    event_dispatcher.register(EventType.EVENT_TICK, lambda event: print(
        f"TICK:{event.data.datetime}: ask1 {event.data.ask_volume_1}@{event.data.ask_price_1}, bid1 {event.data.bid_volume_1}@{event.data.bid_price_1}, last {event.data.trade_volume}@{event.data.trade_price} "))
        # str('TICK: ') + str(event.data)))
        # str('TICK: ') + str(event.data.datetime) +":"+ str(event.data.trade_price)))

    # ok
    # event_dispatcher.register(EventType.EVENT_DEPTH, lambda event: print(
    #     str('DEPTH: ') + str(event.data)))

    # event_dispatcher.register(EventType.EVENT_TRANSACTION, lambda event: print(
    #     str('TRANSACTION: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_ENTRUST, lambda event:  print(str('ENTRUST: ') + str(event.data)))
    # event_dispatcher.register_general(lambda event: print(str(event.type) +  str(event.data)))

    dydx_gateway = DydxGateway(event_dispatcher)
    dydx_gateway.connect(dydx_setting)

    time.sleep(3)

    dydx_gateway.set_subscribe_mode(SubscribeMode(
        transaction=True
    ))

    dydx_gateway.subscribe(SubscribeRequest(
        symbol="BTC-USD", exchange=Exchange.DYDX
    ))

    # from abquant.gateway.dydx import symbol_contract_map

    # print(symbol_contract_map)

    dydx_gateway.start()

    time.sleep(5)

    # 下单撤单
    for i in range(1):
        # ab_order_id = dydx_gateway.send_order(OrderRequest(symbol="BTC-USD", exchange=Exchange.DYDX,
        #                             direction=Direction.SHORT, type=OrderType.LIMIT, 
        #                             price=60000, volume=0.001, offset=Offset.OPEN))
    #     order_id = ab_order_id.split('.')[-1]
    #     print("------open_long",order_id)
        time.sleep(1)
        # dydx_gateway.cancel_order(CancelRequest(order_id, symbol="BTC-USD",exchange=Exchange.DYDX))

    # # cancel all
    print("----------orders",dydx_gateway.orders)
    for order_id in dydx_gateway.orders:
        dydx_gateway.cancel_order(CancelRequest(order_id, symbol="BTC-USD",exchange=Exchange.DYDX))

    # dydx_gateway.send_order(OrderRequest(symbol="BTC-USD", exchange=Exchange.DYDX,
    #                 direction=Direction.LONG, type=OrderType.LIMIT, 
    #                 price=100000, volume=0.001, offset=Offset.CLOSE))


    #  查询历史 在初始化策略时 可以用到该功能。
    # ok
    # history = dydx_gateway.query_history(HistoryRequest(
    #     symbol='BTC-USD', exchange=Exchange.DYDX,
    #     start=datetime(year=2021, month=9, day=3, hour=1, minute=2),
    #     end=datetime(year=2021, month=9, day=6, hour=0, minute=0),
    #     interval=Interval.MINUTE))

    # print('HISTORY: ', history)

        
