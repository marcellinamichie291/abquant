from datetime import datetime
from typing import Dict, List
from logging import getLevelName
import time
from logging import getLevelName

from typing import Dict, List
from abquant.event.event import EventType
from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.event import EventDispatcher, Event
from abquant.gateway import DydxGateway
from abquant.trader.tool import BarAccumulater, BarGenerator

from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import SubscribeMode, SubscribeRequest

import requests
import json

def send_lark(msg):
    url = "https://open.larksuite.com/open-apis/bot/v2/hook/4e58cd69-5fd2-48dd-931c-e489ee5beffa"
    header = {
        "Content-Type": "application/json"
    }
    params ={
        "msg_type":"text",
        "content":{
            "text":f"价格通知:{msg}"
        }
    }
    data = requests.post(url, headers=header,data=json.dumps(params))


class Monitor(StrategyTemplate):
    """监控策略模版"""


    def __init__(self, strategy_runner: LiveStrategyRunner, strategy_name: str, ab_symbols: List[str], setting: dict):
        super().__init__(strategy_runner, strategy_name, ab_symbols, setting)
        self.last_tick_time = None
        self.last_price = {}
        self.last_send_lark_time = time.time()
        

    def on_init(self) -> None:
        self.write_log("策略初始化")

    def on_start(self):
        self.write_log("策略启动")

    def on_stop(self):
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        # 以下的代码是根据tick数据，生成 bars数据的代码。如果策略是分钟级，则不要做任何修改。
        # self.last_price[tick.symbol] = tick.trade_price
        # print(tick)
        pass
        # ETH_price = self.last_price.get("ETHUSDT",0)
        # BTC_price = self.last_price.get("BTCUSDT",0)

        # if ETH_price and BTC_price :
        #     rate = ETH_price / BTC_price
        #     print("eth/btc: ", rate, datetime.now())

        #     if rate < 0.0603 and time.time() - self.last_send_lark_time > 30:
        #         self.last_send_lark_time = time.time()
        #         print("eth/btc: ", rate, self.last_send_lark_time)
        #         send_lark(f"eth/btc: {rate}")


    def on_bars(self, bars: Dict[str, BarData]):
        pass

    def on_exception(self, exception: Exception) -> None:
        print("EXCEPTION" + str(exception))

    def on_window_bars(self, bars: Dict[str, BarData]):
        # window分钟级策略在这里实现， 注意设置 window参数。方便
        pass
        # self.write_log("WINDOW BAR: {}".format(bars))

    def on_entrust(self, entrust: EntrustData) -> None:
        pass

    def on_transaction(self, transaction: TransactionData) -> None:
        pass

    def on_depth(self, depth: DepthData) -> None:
        # print(self.strategy_name, depth.ab_symbol, depth.ask_prices)
        pass

    def on_exception(self, exception: Exception) -> None:
        print("EXCEPTION" + str(exception))

    def on_timer(self, interval: int) -> None:
        # 根据 event dispatcher的 interval 决定， 默认1秒调用一次。
        pass

    def update_trade(self, trade: TradeData) -> None:
        # 成交发生的回调。 可参考父类实现的注释。
        super().update_trade(trade)
        self.write_log("pos update: {} filled with {}. #trade details: {}".format(
            trade.ab_symbol, self.pos[trade.ab_symbol], trade))

    def update_order(self, order: OrderData) -> None:
        # 订单状态改变发生的回调。
        super().update_order(order)
        self.write_log("order still active: {}".format(self.active_orderids))
        self.write_log("order {}, status: {}. #order detail: {}".format(
            order.ab_orderid, order.status, order))



def main():
    dydx_setting = {
        "key": "0ec5b370-74d1-be64-a578-b7bb085ac937",
        "secret": "NLrG3Kuyspe0jt45gENM6UmWGLdSrwj88P-5UPrz",
        "passphrase": "rOkw33sCBiTQhE5PX_GR",
        "stark_private_key": "01a65d7c5fccd96786b0a42ba38df41f58383fcdace4be8581487b61739cc559",
        "proxy_host": "",
        "proxy_port": 0,
        "test_net": ["TESTNET", "REAL"][1],
        "limitFee": 0.001, # makerFeeRate: 0.00050 or takerFeeRate: takerFeeRate: 0.00100
        "accountNumber": 0
    }
    event_dispatcher = EventDispatcher(interval=1)
    event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
        "LOG--{}. {}. gateway: {}; msg: {}".format(
            getLevelName(event.data.level),
            event.data.time,
            event.data.gateway_name,
            event.data.msg)
    ))


    dydx_gateway = DydxGateway(event_dispatcher)
    dydx_gateway.connect(dydx_setting)

    time.sleep(3)
    # subscribe_mode = SubscribeMode(
    #     # 订阅 深度数据 depth. 除非重建orderbook，否则不开也罢。
    #     depth=False,
    #     # 订阅最优五档tick
    #     tick_5=False,
    #     # 订阅best bid/ask tick
    #     best_tick=False,
    #     # 订阅委托单（通常不支持） entrust
    #     entrust=False,
    #     # 订阅交易数据 transaction, 自动生成 tick.
    #     transaction=True
    # )

    # dydx_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)

    strategy_runner = LiveStrategyRunner(event_dispatcher)

    strategy_runner.add_strategy(strategy_class=Monitor,
                                 strategy_name='Monitor',
                                 ab_symbols=["BTC-USD.DYDX",
                                             "ETH-USD.DYDX"],
                                 setting={}
                                 )
    # strategy_runn
    strategy_runner.init_all_strategies()
    time.sleep(1)
    strategy_runner.start_all_strategies()

if __name__ == '__main__':
    main()