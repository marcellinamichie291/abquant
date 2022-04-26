from datetime import datetime, timedelta
import time
import argparse

from abquant.event import EventDispatcher, EventType
from abquant.gateway import FtxGateway
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
}
    event_dispatcher = EventDispatcher()

    # 根据事件类型 注册回调函数。 随意uncomment
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

    # 订阅行情
    # u本位 gateway
    gateway = FtxGateway(event_dispatcher)
    # btc 本位 gateway
    gateway.connect(setting)

    # sleep 是等待交易所 信息与账户信息同步的必要处理。这是异步框架比较丑陋的地方。
    time.sleep(3)
    # 针对minghang策略特殊定制，正常情况无需调用，默认所有数据全部订阅。（除entrust外）想感受各种各样类型的数据的把，一下的depth，tick_5, best_tick项 赋值True，或comment掉下一行代码即可。
    gateway.set_subscribe_mode(SubscribeMode(
        #订阅 深度数据 depth  ok
        depth=False,
        # 最优五档tick  ok
        tick_5=False, 
        # best bid/ask tick  ok
        best_tick=False,
        # 委托单（通常不支持） 
        entrust=False,
        # 交易数据 transaction  ok
        transaction=True)
    )
    gateway.subscribe(SubscribeRequest(
        symbol='ETH/USDT', exchange=Exchange.FTX))
    gateway.subscribe(SubscribeRequest(
        symbol='BTC-PERP', exchange=Exchange.FTX))
    
    # gateway.connect 之后会更新的 binance合约交易的 合约的dict,  symbol_contract_map是全局的一个单例。
    from abquant.gateway.ftx import symbol_contract_map
    print(symbol_contract_map)

    # for i, k in enumerate(symbol_contract_map):
    #     if i > 3:
    #         break
    #     print(i, k, symbol_contract_map[k])
    #     gateway.subscribe(SubscribeRequest(
    #         symbol=k, exchange=Exchange.FTX))
    # subscribe 各个产品后 要调用gateway.start 开始接受数据。该操作较为冗赘，有实现细节上的考虑。 实现strategy时，以上调用对交易员隐藏，由框架实现。
    gateway.start()
    # print("start to receive data from exchange")

    # 下单撤单， 由框架异步执行。胆大的下单撤单吧。不必担心阻塞和 IO。 
    # ok
    
    # for i in range(20):
    ab_order_id: str = gateway.send_order(OrderRequest(symbol='ETH/USDT', exchange=Exchange.FTX,
                                        direction=Direction.LONG, type=OrderType.LIMIT, volume=0.001, price=2800, offset=Offset.OPEN))
    print('ab orderid', ab_order_id)
    time.sleep(3)
    order_id = ab_order_id.split('.')[-1]
    gateway.cancel_order(CancelRequest(
        order_id, symbol='BTCUSDT', exchange=Exchange.FTX))





    #  查询历史 在初始化策略时 可以用到该功能。 OK
    end = datetime.now()
    history = gateway.query_history(HistoryRequest(
        symbol='BTC/USDT', exchange=Exchange.FTX,
        start=end - timedelta(hours=1),
        end=end,
        interval=Interval.MINUTE))
    
    for bar in history:
        print(bar.datetime, bar.close_price)

    # import sys
    # while True:

    #     try:

    #         time.sleep(1)

    #     except KeyboardInterrupt:

    #         sys.exit()