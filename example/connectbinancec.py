from dataclasses import dataclass
from datetime import datetime, timedelta
import sys
from pathlib import Path
import time
import argparse

from abquant.event import EventDispatcher, EventType, Event
from abquant.gateway import BinanceBBCGateway, BinanceUBCGateway
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
    binance_setting = {
        "key": args.key,
        "secret": args.secret,
        "session_number": 20,
        # "127.0.0.1" str类型
        "proxy_host": args.proxy_host if args.proxy_host else "",
        # 1087 int类型
        "proxy_port": args.proxy_port if args.proxy_port else 0,
        "test_net": ["TESTNET", "REAL"][1],
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
    gateway_ = BinanceBBCGateway(event_dispatcher)
    gateway.connect(binance_setting)
    gateway_.connect(binance_setting)

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
    gateway.subscribe(SubscribeRequest(
        symbol='ICPUSDT', exchange=Exchange.BINANCE))

    # gateway.connect 之后会更新的 binance合约交易的 合约的dict,  symbol_contract_map是全局的一个单例。
    from abquant.gateway.binancec import symbol_contract_map

    for i, k in enumerate(symbol_contract_map):
        if i > 3:
            break
        print(i, k, symbol_contract_map[k])
        gateway.subscribe(SubscribeRequest(
            symbol=k, exchange=Exchange.BINANCE))
    # subscribe 各个产品后 要调用gateway.start 开始接受数据。该操作较为冗赘，有实现细节上的考虑。 实现strategy时，以上调用对交易员隐藏，由框架实现。
    gateway.start()
    print("start to receive data from exchange")

    # 下单撤单， 由框架异步执行。胆大的下单撤单吧。不必担心阻塞和 IO。
    for i in range(2):
        ab_order_id: str = gateway.send_order(OrderRequest(symbol='XRPUSDT', exchange=Exchange.BINANCE,
                                            direction=Direction.LONG, type=OrderType.LIMIT, volume=7, price=1.09, offset=Offset.OPEN))
        print('ab orderid', ab_order_id)
        # time.sleep(0.03)
        order_id = ab_order_id.split('.')[-1]
        print('orderid', order_id)
        gateway.cancel_order(CancelRequest(
            order_id, symbol='XRPUSDT', exchange=Exchange.BINANCE))





    #  查询历史 在初始化策略时 可以用到该功能。
    end = datetime.now()
    history = gateway.query_history(HistoryRequest(
        symbol='BTCUSDT', exchange=Exchange.BINANCE,
        start=end - timedelta(days=2),
        end=end,
        interval=Interval.MINUTE))
    
    print(history[1:3])

    history = gateway_.query_history(HistoryRequest(
        symbol='BTCUSD_PERP', exchange=Exchange.BINANCE,
        start=end - timedelta(days=2),
        end=end,
        interval=Interval.MINUTE))
    
    print(history[1:3])

    while True:
        time.sleep(1)
