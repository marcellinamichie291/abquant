from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List
from abquant.trader.common import Direction

from abquant.trader.msg import TradeData


class ContractDailyResult:
    """"""

    def __init__(self, result_date: date, close_price: float):
        """"""
        self.date: date = result_date
        self.close_price: float = close_price
        self.pre_close: float = 0

        self.trades: List[TradeData] = []
        self.trade_count: int = 0

        self.start_pos: float = 0
        self.end_pos: float = 0

        self.turnover: float = 0
        self.commission: float = 0
        self.slippage: float = 0

        self.trading_pnl: float = 0
        self.holding_pnl: float = 0
        self.total_pnl: float = 0
        self.net_pnl: float = 0

    def add_trade(self, trade: TradeData) -> None:
        """"""
        self.trades.append(trade)

    def calculate_pnl(
        self,
        pre_close: float,
        start_pos: float,
        size: int,
        rate: float,
        slippage: float,
        inverse: bool
    ) -> None:
        """"""
        if pre_close:
            self.pre_close = pre_close
        else:
            self.pre_close = 1

        # Holding pnl is the pnl from holding position at day start
        self.start_pos = start_pos
        self.end_pos = start_pos
        if not inverse:
            self.holding_pnl = self.start_pos * \
                (self.close_price - self.pre_close) * size
        else:
            self.holding_pnl = self.start_pos * \
                (1 / self.pre_close - 1 / self.close_price) * size

        self.trade_count = len(self.trades)

        for trade in self.trades:
            if trade.direction == Direction.LONG:
                pos_change = trade.volume
            else:
                pos_change = -trade.volume

            self.end_pos += pos_change

            if not inverse:
                turnover = trade.volume * size * trade.price
                self.trading_pnl += pos_change * \
                    (self.close_price - trade.price) * size
                # self.slippage += trade.volume * size * slippage
            else:
                turnover = trade.volume * size / trade.price
                self.trading_pnl += pos_change * \
                    (1 / trade.price - 1 / self.close_price) * size
                # self.slippage += trade.volume * size * slippage / (trade.price)
            self.turnover += turnover
            self.commission += turnover * rate
            self.slippage += turnover * slippage


        self.total_pnl = self.trading_pnl + self.holding_pnl
        self.net_pnl = self.total_pnl - self.commission - self.slippage

    def update_close_price(self, close_price: float) -> None:
        """"""
        self.close_price = close_price


class ContractsDailyResult:
    """"""

    def __init__(self, result_date: date, close_prices: Dict[str, float]):
        """"""
        self.date: date = result_date
        self.close_prices: Dict[str, float] = close_prices
        self.pre_closes: Dict[str, float] = {}
        self.start_poses: Dict[str, float] = {}
        self.end_poses: Dict[str, float] = {}

        self.contract_results: Dict[str, ContractDailyResult] = {}

        for ab_symbol, close_price in close_prices.items():
            self.contract_results[ab_symbol] = ContractDailyResult(
                result_date, close_price)

        self.trade_count: int = 0
        self.turnover: float = 0
        self.commission: float = 0
        self.slippage: float = 0
        self.trading_pnl: float = 0
        self.holding_pnl: float = 0
        self.total_pnl: float = 0
        self.net_pnl: float = 0
    
    def add_trade(self, trade: TradeData) -> None:
        """"""
        contract_result = self.contract_results[trade.ab_symbol]
        contract_result.add_trade(trade)
    

        

    def calculate_pnl(
        self,
        pre_closes: Dict[str, float],
        start_poses: Dict[str, float],
        sizes: Dict[str, float],
        rates: Dict[str, float],
        slippages: Dict[str, float],
        inverses: Dict[str, bool]
    ) -> None:
        """"""
        self.pre_closes = pre_closes

        if any(inverses.values()) and len(inverses.values()) >= 2:
            raise NotImplementedError("multiple inverse contract will not be supported for a long time.")
        

        for ab_symbol, contract_result in self.contract_results.items():
            contract_result.calculate_pnl(
                pre_closes.get(ab_symbol, 0),
                start_poses.get(ab_symbol, 0),
                sizes[ab_symbol],
                rates[ab_symbol],
                slippages[ab_symbol],
                inverses[ab_symbol]
            )

            self.trade_count += contract_result.trade_count
            self.turnover += contract_result.turnover
            self.commission += contract_result.commission
            self.slippage += contract_result.slippage
            self.trading_pnl += contract_result.trading_pnl
            self.holding_pnl += contract_result.holding_pnl
            self.total_pnl += contract_result.total_pnl
            self.net_pnl += contract_result.net_pnl

            self.end_poses[ab_symbol] = contract_result.end_pos

    def update_close_prices(self, close_prices: Dict[str, float]) -> None:
        """"""

        for ab_symbol, close_price in close_prices.items():

            self.close_prices[ab_symbol] = close_price
            contract_result = self.contract_results.get(ab_symbol, None)
            if contract_result:
                contract_result.update_close_price(close_price)
            else:
                self.contract_results[ab_symbol] = ContractDailyResult(
                    self.date, close_price)


