
from datetime import datetime
from re import S
import threading
from typing import Dict, List
import argparse
from logging import getLevelName
import time
import numpy as np
from pprint import pprint
from abquant.monitor.monitor import Monitor

from abquant.trader.tool import BarAccumulater, BarGenerator
from abquant.trader.common import Direction, Exchange, Offset, OrderType, Status
from abquant.trader.utility import extract_ab_symbol, generate_ab_symbol, round_to, round_up
from abquant.event.event import EventType
from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.event import EventDispatcher, Event
from abquant.gateway import BinanceUBCGateway, BinanceBBCGateway, BitmexGateway
from abquant.gateway.bitmex import symbol_contract_map as bitmex_symbol_contract_map
# from abquant.gateway.binancec import symbol_contract_map as binance_symbol_contract_map
from abquant.trader.msg import BarData, DepthData, EntrustData, OrderData, TickData, TradeData, TransactionData
from abquant.trader.object import SubscribeMode
from abquant.trader.tool import ArrayCache

# 命令行参数的解析代码，交易员可以不用懂。


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


def calculate_grid(ab_symbol, upper_bound, lower_bound, num):
    symbol, _ = extract_ab_symbol(ab_symbol)
    contract = bitmex_symbol_contract_map[symbol]
    prices = []
    rate = (upper_bound / lower_bound) ** (1 / num) - 1
    current_grid_price = lower_bound
    while True:
        if current_grid_price > upper_bound:
            break
        prices.append(current_grid_price)
        current_grid_price *= (1 + rate)
    prices = [round_to(price, contract.pricetick) for price in prices][:num]
    return prices, rate


# 策略的实现，所有细节都需要明确。务必先看完.
class GridStrategy(StrategyTemplate):
    # 以下类属性/成员， 均由交易员自行决定并声明。
    window = 15
    history = 300
    lower_bound_multipler = 0.8
    upper_bound_multipler = 1.2
    grid_num = 40
    U_per_trade = 100

    # 声明可配置参数，本行之上是可配置参数的默认值。
    parameters = [
        "window",
        "lower_bound_multipler",
        "upper_bound_multipler",
        "grid_num",
        "U_per_trade",
        "history"
    ]
    # 声明未来可能出现的，可能需盘中纪录的可计算参数， 如需监控的因子值，以及各金融产品的仓位变化等等， 后续提供支持。
    variables = [
    ]

    def __init__(
        self,
        strategy_engine: LiveStrategyRunner,
        strategy_name: str,
        ab_symbols: List[str],
        setting: dict
    ):
        """"""

        super().__init__(strategy_engine, strategy_name, ab_symbols, setting)
        self.bgs: Dict[str, BarGenerator] = {}
        self.last_tick_time = None
        self.rate = 0

    def on_init(self):
        for ab_symbol in self.ab_symbols:
            self.bgs[ab_symbol] = BarGenerator(lambda bar: None, interval=1)
        self.array_cache = ArrayCache(self.window * self.history)
        self.grid_orders: Dict[str, OrderData] = {}
        self.reduce_orders: Dict[str, OrderData] = {}

        # init时 从交易所获取过去n 天的1 分钟k线。生成 60 * 24 个供 strategy.on_bars 调用的 bars: Dict[str, BarData], 字典的key是 ab_symbol, value是BarData.
        # 从交易所获取后，顺序调用on_bars 60 * 24 次，再返回。
        # 由于是strategy实例尚未 start，因此在on_bars中调用的下单请求，不会发送，同时处理回报的update_order/trade 方法也不会被调用。
        # 即load_bars 方法适用于 需要根据历史k线预热的策略。 比如计算3日均线。使用该方法，可以避免strategy实例，上线后预热3日后正式开始交易。
        n_days = int(self.window * self.history / (24 * 60)) + 1
        self.write_log("replay the last {} days.".format(n_days))
        self.load_bars(n_days)
        self.write_log("replay done.")
        self.write_log("策略初始化")

    def on_start(self):
        self.write_log("策略启动")

    def on_stop(self):
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        # 以下的代码是根据tick数据，生成 bars数据的代码。如果策略是分钟级，则不要做任何修改。
        if (
            self.last_tick_time and
            tick.datetime > self.last_tick_time and
            self.last_tick_time.minute != tick.datetime.minute
        ):
            bars = {}
            for ab_symbol, bg in self.bgs.items():
                bars[ab_symbol] = bg.generate()
            # 生成新的k线数据后，主动调用 on_bars。
            # self.write_log("new minutes tick: {}".format(tick))
            if all(bars.values()):
                self.on_bars(bars)

        bg: BarGenerator = self.bgs[tick.ab_symbol]
        bg.update_tick(tick)
        if self.last_tick_time:
            self.last_tick_time = tick.datetime if tick.datetime > self.last_tick_time else self.last_tick_time
        else:
            self.last_tick_time = tick.datetime

    def on_bars(self, bars: Dict[str, BarData]):
        ab_symbol = self.ab_symbols[0]
        close_price = bars[ab_symbol].close_price
        self.array_cache.update_bar(bars[ab_symbol])
        if not self.array_cache.inited:
            return
        window_close_array = []
        for i in range(0, self.window * self.history, self.window):
            window_close_array.append(self.array_cache.close[i])
        if not self.trading:
            return

        mean_close = np.mean(np.array(window_close_array))
        self.mean_close = mean_close
        self.write_log("mean: {}, now: {}".format(mean_close, close_price))
        if mean_close > close_price:
            prices, self.rate = calculate_grid(
                ab_symbol, mean_close*self.upper_bound_multipler, mean_close, self.grid_num)
            self.check_refill(ab_symbol, prices, direction=Direction.SHORT)

        else:
            prices, self.rate = calculate_grid(
                ab_symbol, mean_close, mean_close*self.lower_bound_multipler, self.grid_num)
            self.check_refill(ab_symbol, prices, direction=Direction.LONG)

    def check_refill(self, ab_symbol, prices, direction: Direction):
        self.write_log("price to placed: {}".format(prices))
        for aborder_id, order in self.grid_orders.items():
            if order is None:
                continue
            if order.price not in prices:
                self.cancel_order(aborder_id)
        orders_prices = [
            order.price for order in self.grid_orders.values() if order]
        self.write_log("price in grids: {}".format(orders_prices))
        reduce_orders_prices = [
            order.price for order in self.reduce_orders.values() if order]
        self.write_log("price in reduce: {}".format(reduce_orders_prices))
        for price in prices:
            if price not in orders_prices:
                # volumn = self.U_per_trade / price
                # TODO inverse contract
                volumn = self.U_per_trade
                ab_orderids = self.send_order(
                    ab_symbol, direction, price, volumn, Offset.OPEN, OrderType.LIMIT)
                ab_orderid = ab_orderids[0] if len(ab_orderids) > 0 else None
                if ab_orderid is None:
                    continue
                self.grid_orders[ab_orderid] = None

    def on_window_bars(self, bars: Dict[str, BarData]):
        # window分钟级策略在这里实现， 注意设置 window参数。方便
        pass

    def on_entrust(self, entrust: EntrustData) -> None:
        pass

    def on_transaction(self, transaction: TransactionData) -> None:
        # print(self.strategy_name, transaction)
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
        # self.write_log("pos update: {} filled with {}. #trade details: {}".format(
        #     trade.ab_symbol, self.pos[trade.ab_symbol], trade))

    def update_order(self, order: OrderData) -> None:
        # 订单状态改变发生的回调。
        super().update_order(order)
        if order.status == Status.SUBMITTING:
            if order.ab_orderid in self.grid_orders.keys():
                self.grid_orders[order.ab_orderid] = order
            if order.ab_orderid in self.reduce_orders.keys():
                self.reduce_orders[order.ab_orderid] = order

        elif order.status == Status.ALLTRADED:
            if order.ab_orderid in self.grid_orders.keys():
                self.write_log("grid order filled: {}".format(order))
                self.grid_orders.pop(order.ab_orderid)

                direction = Direction.LONG if order.direction == Direction.SHORT else Direction.SHORT
                price = order.price * \
                    (1 - self.rate) if order.direction == Direction.SHORT else order.price * (1 + self.rate)

                volumn = order.volume
                ab_orderids = self.send_order(
                    order.ab_symbol, direction, price, volumn, Offset.OPEN, OrderType.LIMIT)

                self.write_log(
                    "reduce order sent: price: {}, dir: {}".format(price, direction))
                if ab_orderids:
                    self.reduce_orders[ab_orderids[0]] = None

                # self.

            if order.ab_orderid in self.reduce_orders:

                self.write_log("reduce order filled: {}".format(order))
                self.reduce_orders.pop(order.ab_orderid)
                mean_close = self.mean_close
                close_price = order.price
                if mean_close > close_price:
                    prices, self.rate = calculate_grid(
                        order.ab_symbol, mean_close*self.upper_bound_multipler, mean_close, self.grid_num)
                    self.check_refill(order.ab_symbol, prices,
                                      direction=Direction.SHORT)

                else:
                    prices, self.rate = calculate_grid(
                        order.ab_symbol, mean_close, mean_close*self.lower_bound_multipler, self.grid_num)
                    self.check_refill(order.ab_symbol, prices,
                                      direction=Direction.LONG)

        elif order.status == Status.CANCELLED:
            if order.ab_orderid in self.grid_orders.keys():
                self.grid_orders.pop(order.ab_orderid)
            if order.ab_orderid in self.reduce_orders:
                self.reduce_orders.pop(order.ab_orderid)
        elif order.status == Status.REJECTED:
            self.write_log("order rejected: {}".format(order))
            if order.ab_orderid in self.grid_orders.keys():
                self.grid_orders.pop(order.ab_orderid)
            if order.ab_orderid in self.reduce_orders:
                self.reduce_orders.pop(order.ab_orderid)
            ab_orderids = self.send_order(
                order.ab_symbol, order.direction, order.price, order.volume, order.offset, order.type)
            if ab_orderids:
                if ab_orderids:
                    self.reduce_orders[ab_orderids[0]] = None


def main():
    args = parse()
    bitmex_setting = {
        "key": args.key,
        "secret": args.secret,
        "session_number": 10,
        # "127.0.0.1" str类型
        "proxy_host": args.proxy_host if args.proxy_host else "",
        # 1087 int类型
        "proxy_port": args.proxy_port if args.proxy_port else 0,
        "test_net": ["TESTNET", "REAL"][0],
    }

    event_dispatcher = EventDispatcher(interval=1)
    common_setting = {
        "username": "zhanghui",
        "password": "123456",
    }
    # Monitor.init_monitor(common_setting)
    monitor = Monitor(common_setting)
    monitor.start()

    strategy_runner = LiveStrategyRunner(event_dispatcher)
    strategy_runner.set_monitor(monitor)
    # 注册一下 log 事件的回调函数， 该函数决定了如何打log。
    # event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(
    #     "LOG--{}. {}. gateway: {}; msg: {}".format(
    #         getLevelName(event.data.level),
    #         event.data.time,
    #         event.data.gateway_name,
    #         event.data.msg)
    # ))
    # event_dispatcher.register(EventType.EVENT_ACCOUNT, lambda event: print(
    #     str('ACCOUNT: ') + str(event.data)))  # pass accessor,  trade_listerer not done
    # event_dispatcher.register(EventType.EVENT_CONTRACT, lambda event:  print(str('CONTRACT: ') + str(event.data))) # pass
    # event_dispatcher.register(EventType.EVENT_POSITION, lambda event: print(
    #     str('POSITION: ') + str(event.data)))

    # binance_bbc_gateway = BinanceBBCGateway(event_dispatcher)
    # binance_bbc_gateway.connect(binance_setting)

    bitmex_gateway = BitmexGateway(event_dispatcher)
    bitmex_gateway.connect(bitmex_setting)

    # 等待连接成功。
    time.sleep(15)
    subscribe_mode = SubscribeMode(
        # 订阅 深度数据 depth. 除非重建orderbook，否则不开也罢。
        depth=False,
        # 订阅最优五档tick
        tick_5=True,
        # 订阅best bid/ask tick
        best_tick=True,
        # 订阅委托单（通常不支持） entrust
        entrust=False,
        # 订阅交易数据 transaction, 自动生成 tick.
        transaction=True
    )

    # 有默认值，默认全订阅, 可以不调用下面两行。
    bitmex_gateway.set_subscribe_mode(subscribe_mode=subscribe_mode)


    from abquant.gateway.bitmex import symbol_contract_map
    for k, v in symbol_contract_map.items():
        print(v)
    ab_symbols = [generate_ab_symbol(
        symbol, exchange=Exchange.BITMEX) for symbol in symbol_contract_map.keys()]
    # this is subscribe all
    time.sleep(5)
    print("{} instrument symbol could be subscribed: ".format(
        len(ab_symbols)), ab_symbols)
    # strategy 订阅所有binance合约 的金融产品行情数据。
    # strategy_runner.add_strategy(strategy_class=TheStrategy,
    #                              strategy_name='the_strategy0',
    #                              ab_symbols=ab_symbols,
    #                              setting={"param1": 1, "param2": 2}
    #                              )
    strategy_runner.add_strategy(strategy_class=GridStrategy,
                                 strategy_name='the_strategy1',
                                 #  ab_symbols=["XBTUSD.BITMEX"],
                                 # TODO 选产品
                                 ab_symbols=["XBTUSD.BITMEX"],
                                 #  ab_symbols=["BTCUSDT.BINANCE"],
                                 setting={
                                     "window": 2,
                                     "lower_bound_multipler": 0.995,
                                     "upper_bound_multipler": 1.005,
                                     "grid_num": 4,
                                     "U_per_trade": 100,
                                     "history": 5}
                                 )
    strategy_runner.init_all_strategies()

    # 策略 start之前 sleepy一段时间， 新的策略实例有可能订阅新的产品行情，这使得abquant需要做一次与交易所的重连操作。
    time.sleep(10)
    strategy_runner.start_all_strategies()

    import random
    while True:
        time.sleep(1)


    # print([c.func.id for c in ast.walk(ast.parse(inspect.getsource(TheStrategy))) if isinstance(c, ast.Call)])
if __name__ == '__main__':
    main()
    # test()
