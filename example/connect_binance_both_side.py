import time

from abquant.event import EventDispatcher, EventType
from abquant.gateway import BinanceBBCGateway, BinanceUBCGateway
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeMode, SubscribeRequest
from abquant.trader.common import Direction, Exchange, Interval, Offset, OrderType




if __name__ == '__main__':
    binance_setting = {
        "key": "cea51b2a312e0ec837568a1b98c89c8f0f53cfb141d72cdd8aa5a124434fd3f5",
        "secret": "959feddbdbbbd96b0c64833458891a49c911f9605fcfef5aa200069a23ea98cd",
        "session_number": 2,
        # "127.0.0.1" str类型
        "proxy_host": "127.0.0.1",
        # 1087 int类型
        "proxy_port": 7899,
        "test_net": ["TESTNET", "REAL"][0],
        "position_mode":["One-way", "Hedge"][1],

    }
    event_dispatcher = EventDispatcher()

    # 根据事件类型 注册回调函数。 随意uncomment
    event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
        str('LOG: ') + str(event.data)))  # pass
    # # event_dispatcher.register(EventType.EVENT_TIMER, lambda event:  print(str('TIMER: ') + str(event.data))) #pass
    # event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(
    #     str('ACCOUNT: ') + str(event.data)))  # pass accessor,  trade_listerer not done
    # event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data))) # pass
    event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(
        str('POSITION: ') + str(event.data)))  # pass accessor, trade_listerer not done
    event_dispatcher.register(EventType.EVENT_EXCEPTION, lambda event: print(
        str('EXCEPTION: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_ORDER, lambda event: print(
    #     str('ORDER: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_TRADE, lambda event: print(
    #     str('TRADE: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_TICK, lambda event: print(
    #     str('TICK: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_DEPTH, lambda event: print(
    #     str('DEPTH: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_TRANSACTION, lambda event: print(
    #     str('TRANSACTION: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_ENTRUST, lambda event:  print(str('ENTRUST: ') + str(event.data)))
    # event_dispatcher.register_general(lambda event: print(str(event.type) +  str(event.data)))

    # 订阅行情
    # u本位 gateway
    gateway = BinanceUBCGateway(event_dispatcher)
    # btc 本位 gateway
    # gateway_ = BinanceBBCGateway(event_dispatcher)
    gateway.connect(binance_setting)
    # gateway_.connect(binance_setting)

    # sleep 是等待交易所 信息与账户信息同步的必要处理。这是异步框架比较丑陋的地方。
    time.sleep(3)
    # 针对minghang策略特殊定制，正常情况无需调用，默认所有数据全部订阅。（除entrust外）想感受各种各样类型的数据的把，一下的depth，tick_5, best_tick项 赋值True，或comment掉下一行代码即可。
    gateway.set_subscribe_mode(SubscribeMode(
        #订阅 深度数据 depth
        depth=False,
        # 最优五档tick
        tick_5=False,
        # best bid/ask tick
        best_tick=False,
        # 委托单（通常不支持） entrust
        entrust=False,
        # 交易数据 transaction
        transaction=True)
    )
    # 下单撤单， 由框架异步执行。胆大的下单撤单吧。不必担心阻塞和 IO。
    
    # for i in range(20):
    #     ab_order_id: str = gateway.send_order(OrderRequest(symbol='XRPUSDT', exchange=Exchange.BINANCE,
    #                                         direction=Direction.LONG, type=OrderType.POSTONLYLIMIT, volume=10.00001, price=0.5, offset=Offset.OPEN))
    #     print('ab orderid', ab_order_id)
    #     time.sleep(1)
    #     order_id = ab_order_id.split('.')[-1]
    #     print('orderid', order_id)
    #     gateway.cancel_order(CancelRequest(
    #         order_id, symbol='XRPUSDT', exchange=Exchange.BINANCE))
    # 开多
    ab_order_id: str = gateway.send_order(OrderRequest(symbol='BTCUSDT', exchange=Exchange.BINANCE,
                                            direction=Direction.LONG, type=OrderType.LIMIT, volume=0.01, price=43000, offset=Offset.OPEN))
    # 开空
    ab_order_id: str = gateway.send_order(OrderRequest(symbol='BTCUSDT', exchange=Exchange.BINANCE,
                                            direction=Direction.SHORT, type=OrderType.LIMIT, volume=0.01, price=40000, offset=Offset.OPEN))
    # 平多
    ab_order_id: str = gateway.send_order(OrderRequest(symbol='BTCUSDT', exchange=Exchange.BINANCE,
                                            direction=Direction.SHORT, type=OrderType.MARKET, volume=0.01, price=43000, offset=Offset.CLOSE))
    # # 平空
    # ab_order_id: str = gateway.send_order(OrderRequest(symbol='BTCUSDT', exchange=Exchange.BINANCE,
    #                                         direction=Direction.LONG, type=OrderType.MARKET, volume=0.01, price=40000, offset=Offset.CLOSE))


    # def buy(self, ab_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.MARKET) -> List[str]:
    #     """
    #     开多。
    #     注意事项：
    #     1. 有些交易所不存在Offset的概念。全部使用Offset.Open可行（如bitmex），但建议策略师依旧能够使用offset， 一方面，订单撮合存在时差，在高频做市策略里这是很有必要的保证空仓的机制，二来，回测时不会累计垃圾订单。
    #     2. 买卖会自动处理price tick的问题（最小可变价格），但依旧建议策略师编写师都做好价格round。尤其是做市类策略。

    #     """
    #     return self.send_order(ab_symbol, Direction.LONG, price, volume, Offset.OPEN, order_type)

    # def sell(self, ab_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.MARKET) -> List[str]:
    #     """
    #     平多
    #     """
    #     return self.send_order(ab_symbol, Direction.SHORT, price, volume, Offset.CLOSE, order_type)

    # def short(self, ab_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.MARKET) -> List[str]:
    #     """
    #     开空
    #     """
    #     return self.send_order(ab_symbol, Direction.SHORT, price, volume,  Offset.OPEN, order_type)

    # def cover(self, ab_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.MARKET) -> List[str]:
    #     """
    #     平空 
    #     """
    #     return self.send_order(ab_symbol, Direction.LONG, price, volume, Offset.CLOSE, order_type)

