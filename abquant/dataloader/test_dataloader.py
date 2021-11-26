from datetime import datetime
import threading
from typing import Dict, List
import argparse
from logging import getLevelName
import time
from pprint import pprint
from abquant.gateway.binances.binancegateway import BinanceSGateway

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

# 命令行参数的解析代码，交易员可以不用懂。
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
    binance_setting = {
        "key": args.key,
        "secret": args.secret,
        "session_number": 3,
        # "127.0.0.1" str类型
        "proxy_host": args.proxy_host if args.proxy_host else "",
        # 1087 int类型
        "proxy_port": args.proxy_port if args.proxy_port else 0,
        "test_net": ["TESTNET", "REAL"][1],
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


    # print([c.func.id for c in ast.walk(ast.parse(inspect.getsource(TheStrategy))) if isinstance(c, ast.Call)])
if __name__ == '__main__':
    main()
    # test()
