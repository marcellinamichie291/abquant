
from datetime import datetime
import threading
from typing import Dict, List
import argparse
from logging import getLevelName
import time
from pprint import pprint
from abquant.gateway import BitmexGateway

from abquant.trader.tool import BarAccumulater, BarGenerator
from abquant.trader.common import Exchange, OrderType
from abquant.trader.utility import generate_ab_symbol, round_up
from abquant.event.event import EventType
from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.event import EventDispatcher, Event
from abquant.gateway import BinanceUBCGateway, BinanceBBCGateway
from abquant.monitor import Monitor
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import SubscribeMode


from strategy.doublemeanaverage import DoubleMAStrategy


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', type=str, required=True,
                        help='api key')
    parser.add_argument('-s', '--secret', type=str, required=True,
                        help='api secret')
    parser.add_argument('-t', '--strategy', type=str, required=True,
                        help='策略分类名称，找@yaqiang添加')
    parser.add_argument('-l', '--log_path', type=str, required=False,
                        help='监控日志路径，默认本地logs文件夹')
    parser.add_argument('-u', '--proxy_host', type=str,
                        # default='127.0.0.1',
                        help='proxy host')
    parser.add_argument('-p', '--proxy_port', type=int,
                        help='proxy port')
    args = parser.parse_args()
    return args



def main():
    args = parse()
    bitmex_setting = {
        "key": args.key,
        "secret": args.secret,
        "session_number": 3,
        # "127.0.0.1" str类型
        "proxy_host": args.proxy_host if args.proxy_host else "",
        # 1087 int类型
        "proxy_port": args.proxy_port if args.proxy_port else 0,
        "test_net": ["TESTNET", "REAL"][0],
    }

    common_setting = {
        "strategy": args.strategy,
        "lark_url": None,  # "https://open.larksuite.com/open-apis/bot/v2/hook/2b92f893-83c2-48c1-b366-2e6e38a09efe",
        "log_path": args.log_path,
    }
    # Monitor.init_monitor(common_setting)
    # 初始化 monitor
    monitor = Monitor(common_setting)
    monitor.start()

    event_dispatcher = EventDispatcher(interval=1)
    strategy_runner = LiveStrategyRunner(event_dispatcher)
    #设置monitor
    strategy_runner.set_monitor(monitor)

    # 注册一下 log 事件的回调函数， 该函数决定了如何打log。
    # event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
    #     "LOG--{}. {}. gateway: {}; msg: {}".format(
    #         getLevelName(event.data.level),
    #         event.data.time,
    #         event.data.gateway_name,
    #         event.data.msg)
    # ))
    subscribe_mode = SubscribeMode(
        # 订阅 深度数据 depth. 除非重建orderbook，否则不开也罢。
        depth=False,
        # 订阅最优五档tick
        tick_5=False,
        # 订阅best bid/ask tick
        best_tick=False,
        # 订阅委托单（通常不支持） entrust
        entrust=False,
        # 订阅交易数据 transaction, 自动生成 tick.
        transaction=True
    )

    bitmex_gateway = BitmexGateway(event_dispatcher)
    bitmex_gateway.connect(bitmex_setting)

    time.sleep(20)

    from abquant.gateway.bitmex import symbol_contract_map
    for k, v in symbol_contract_map.items():
        print(v)
    ab_symbols = [generate_ab_symbol(
        symbol, exchange=Exchange.BITMEX) for symbol in symbol_contract_map.keys()]
    # this is subscribe all
    time.sleep(5)
    print("{} instrument symbol strategy0 subscribed: ".format(
        len(ab_symbols)), ab_symbols)

    strategy_runner.add_strategy(strategy_class=DoubleMAStrategy,
                                 strategy_name='the_strategy',
                                 ab_symbols=["XBTUSD.BITMEX"],
                                 # uncommnet for test trade operation.
                                 setting={}
                                 )
    strategy_runner.init_all_strategies()

    # 策略 start之前 sleepy一段时间， 新的策略实例有可能订阅新的产品行情，这使得abquant需要做一次与交易所的重连操作。
    time.sleep(5)
    strategy_runner.start_all_strategies()
    # monitor.send_notify_lark("11111111", "message for lark", common_setting.get("lark_url"))

    import random
    while True:
        time.sleep(300)









if __name__ == '__main__':
    main()
    # test()