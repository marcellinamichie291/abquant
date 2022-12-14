from datetime import datetime, timedelta
from itertools import chain
from typing import Dict, Iterable, Optional, Tuple, overload

from abquant.trader.common import Direction, Interval, OrderType, Status
from abquant.trader.msg import BarData, TickData, TradeData
from abquant.trader.object import OrderData
from .orderbook import OrderBook


class BarOrderBook(OrderBook):
    def __init__(self):
        super(BarOrderBook, self).__init__()
        self.bars: Dict[str, BarData] = {}
        # self.datetime: datetime = None
        self.interval = Interval.MINUTE
        self.trade_count = 0

    def newest_bars(self) -> Dict[str, BarData]:
        return self.bars

    def update_bar(self, bar: BarData) -> None:
        last_bar = self.bars.get(bar.ab_symbol, None)
        if last_bar and bar.datetime - last_bar.datetime != timedelta(minutes=1):
            print(
                "Warning: bar.datetime - self.bars[bar.ab_symbol] != timedelta(minutes=1)")
            print("last_bar: {}".format(last_bar))
            print("bar: {}".format(bar))

        self.bars[bar.ab_symbol] = bar

    def insert_order(self, order: OrderData) -> str:
        return super().insert_order(order)

    def cancel_order(self, ab_orderid: str) -> Optional[OrderData]:
        return super().cancel_order(ab_orderid)

    def check_datetime(self) -> None:
        iterator = iter(self.bars.values())
        try:
            first = next(iterator)
        except StopIteration:
            return True
        return all(first.datetime == x.datetime for x in iterator)

    def match_orders(self) -> Iterable[Tuple[OrderData, TradeData]]:
        if not self.check_datetime():
            raise RuntimeError(
                "BarOrderBook.match_orders: bars not all in the same minute, bars, {}".format(self.bars))

        for order in list(self.active_limit_orders.values()):
            if order.type not in self.SUPPORTED_ORDERTYPE:
                raise ValueError(
                    "ordertype other than {} are not supported yet.".format(self.SUPPORTED_ORDERTYPE))
            bar = self.bars[order.ab_symbol]

            long_cross_price = bar.low_price
            short_cross_price = bar.high_price
            long_best_price = bar.open_price
            short_best_price = bar.open_price

            long_cross = (
                order.direction == Direction.LONG
                and order.price >= long_cross_price
                and long_cross_price > 0
            )

            short_cross = (
                order.direction == Direction.SHORT
                and order.price <= short_cross_price
                and short_cross_price > 0
            )

            if not long_cross and not short_cross:
                continue

            # Push order update with status "all traded" (filled).
            order.traded = order.volume
            order.status = Status.ALLTRADED

            self.active_limit_orders.pop(order.ab_orderid)

            if long_cross:
                trade_price = min(order.price, long_best_price)
            else:
                trade_price = max(order.price, short_best_price)

            self.trade_count += 1
            trade = TradeData(
                symbol=order.symbol,
                exchange=order.exchange,
                orderid=order.orderid,
                tradeid=str(self.trade_count),
                direction=order.direction,
                offset=order.offset,
                price=trade_price,
                volume=order.volume,
                datetime=bar.datetime,
                gateway_name=order.gateway_name,
            )
            yield (order, trade)
        

        for order in list(self.stop_market_orders.values()):
            if order.type not in self.SUPPORTED_ORDERTYPE:
                raise ValueError(
                    "ordertype other than {} are not supported yet.".format(self.SUPPORTED_ORDERTYPE))
            bar = self.bars[order.ab_symbol]

            long_cross_price = bar.high_price
            short_cross_price = bar.low_price
            long_worst_price = bar.open_price
            short_worst_price = bar.open_price

            long_cross = (
                order.direction == Direction.LONG
                and order.price <= long_cross_price
                and long_cross_price > 0
            )

            short_cross = (
                order.direction == Direction.SHORT
                and order.price >= short_cross_price
                and short_cross_price > 0
            )

            if not long_cross and not short_cross:
                continue

            # Push order update with status "all traded" (filled).
            order.traded = order.volume
            order.status = Status.ALLTRADED

            if long_cross:
                trade_price = long_worst_price if order.price < long_worst_price else order.price
            else:
                trade_price = short_worst_price if order.price > short_worst_price else order.price

            self.stop_market_orders.pop(order.ab_orderid)


            self.trade_count += 1
            trade = TradeData(
                symbol=order.symbol,
                exchange=order.exchange,
                orderid=order.orderid,
                tradeid=str(self.trade_count),
                direction=order.direction,
                offset=order.offset,
                price=trade_price,
                volume=order.volume,
                datetime=bar.datetime,
                gateway_name=order.gateway_name,
            )
            yield (order, trade)
