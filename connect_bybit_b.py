from datetime import datetime, timedelta
import time
import argparse

from abquant.event import EventDispatcher, EventType
from abquant.gateway import BybitBBCGateway
from abquant.trader.object import CancelRequest, HistoryRequest, OrderRequest, SubscribeMode, SubscribeRequest
from abquant.trader.common import Direction, Exchange, Interval, Offset, OrderType


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
    setting = {
        "key": args.key,
        "secret": args.secret,
        # "127.0.0.1" str类型
        "proxy_host": args.proxy_host if args.proxy_host else "",
        # 1087 int类型
        "proxy_port": args.proxy_port if args.proxy_port else 0,
        "test_net": ["TESTNET", "REAL"][0],
}
    event_dispatcher = EventDispatcher()

    # 根据事件类型 注册回调函数。 随意uncomment
    event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
        str('LOG: ') + str(event.data)))  # ok
    # event_dispatcher.register(EventType.EVENT_TIMER, lambda event:  print(str('TIMER: ') + str(event.data))) #pass
    # event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(
    #     str('ACCOUNT: ') + str(event.data)))  # ok
    # event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data))) # pass
    event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(
        str('POSITION: ') + str(event.data)))  # ok
    event_dispatcher.register(EventType.EVENT_EXCEPTION, lambda event: print(
        str('EXCEPTION: ') + str(event.data)))
    event_dispatcher.register(EventType.EVENT_ORDER, lambda event: print(
        str('ORDER: ') + str(event.data)))
    event_dispatcher.register(EventType.EVENT_TRADE, lambda event: print(
        str('TRADE: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_TICK, lambda event: print(
    #     str('TICK: ') + str(event.data))) # ok
    event_dispatcher.register(EventType.EVENT_DEPTH, lambda event: print(
        str('DEPTH: ') + str(event.data))) #ok
    # event_dispatcher.register(EventType.EVENT_TRANSACTION, lambda event: print(
    #     str('TRANSACTION: ') + str(event.data)))
    # event_dispatcher.register(EventType.EVENT_ENTRUST, lambda event:  print(str('ENTRUST: ') + str(event.data)))
    # event_dispatcher.register_general(lambda event: print(str(event.type) +  str(event.data)))

    # 订阅行情
    # u本位 gateway
    gateway = BybitBBCGateway(event_dispatcher)
    # btc 本位 gateway
    gateway.connect(setting)

    # sleep 是等待交易所 信息与账户信息同步的必要处理。这是异步框架比较丑陋的地方。
    time.sleep(3)
    # 针对minghang策略特殊定制，正常情况无需调用，默认所有数据全部订阅。（除entrust外）想感受各种各样类型的数据的把，一下的depth，tick_5, best_tick项 赋值True，或comment掉下一行代码即可。
    gateway.set_subscribe_mode(SubscribeMode(
        #订阅 深度数据 depth
        depth=True,
        # 最优五档tick
        tick_5=True,
        # best bid/ask tick
        best_tick=True,
        # 委托单（通常不支持） entrust
        entrust=False,
        # 交易数据 transaction
        transaction=True)
    )
    gateway.subscribe(SubscribeRequest(
        symbol='BTCUSD', exchange=Exchange.BYBIT))

    # gateway.connect 之后会更新的 binance合约交易的 合约的dict,  symbol_contract_map是全局的一个单例。
    from abquant.gateway.bybit import bbc_symbol_contract_map, future_symbol_contract_map
    # print(bbc_symbol_contract_map)
    # print(future_symbol_contract_map)

    # for i, k in enumerate(symbol_contract_map):
    #     if i > 3:
    #         break
    #     print(i, k, symbol_contract_map[k])
    #     gateway.subscribe(SubscribeRequest(
    #         symbol=k, exchange=Exchange.BYBIT))
    # subscribe 各个产品后 要调用gateway.start 开始接受数据。该操作较为冗赘，有实现细节上的考虑。 实现strategy时，以上调用对交易员隐藏，由框架实现。
    gateway.start()
    # print("start to receive data from exchange")

    # 下单撤单， 由框架异步执行。胆大的下单撤单吧。不必担心阻塞和 IO。 
    # ok
    time.sleep(3)
    
    # for i in range(20):
    ab_order_id: str = gateway.send_order(OrderRequest(symbol='BTCUSD', exchange=Exchange.BYBIT,
                                        direction=Direction.LONG, type=OrderType.POSTONLYLIMIT, volume=1, price=48000.50, offset=Offset.OPEN))
    
    
    ab_order_id1: str = gateway.send_order(OrderRequest(symbol='BTCUSD', exchange=Exchange.BYBIT,
                                        direction=Direction.LONG, type=OrderType.LIMIT, volume=1, price=44000.50, offset=Offset.OPEN))
    print('ab orderid', ab_order_id1)
    time.sleep(3)
    order_id = ab_order_id1.split('.')[-1]
    # print('orderid', order_id)
    gateway.cancel_order(CancelRequest(
        order_id, symbol='BTCUSD', exchange=Exchange.BYBIT))





    #  查询历史 在初始化策略时 可以用到该功能。 OK
    # end = datetime.now()
    # history = gateway.query_history(HistoryRequest(
    #     symbol='BTCUSD', exchange=Exchange.BYBIT,
    #     start=end - timedelta(days=1),
    #     end=end,
    #     interval=Interval.MINUTE))
    
    # print(history)

    # while True:
    #     time.sleep(1)
