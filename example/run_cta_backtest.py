
from datetime import datetime
from abquant.dataloader import DataLoaderKline
from abquant.strategytrading import BacktestStrategyRunner, BacktestingMode
from abquant.trader.common import Interval
from strategy.doublemeanaverage import DoubleMAStrategy


if __name__ == '__main__':
    dt_setting = {}
    start = datetime(2021, 12, 1)
    end = datetime(2020, 12, 12)
    dataloader: DataLoaderKline = DataLoaderKline(dt_setting)
    dataset = dataloader.load_data('ETHUSDT.BINANCE', start, end)

    backtest_strategy_runner = BacktestStrategyRunner()
    backtest_strategy_runner.set_data_loader(dataloader)

    ab_symbol = 'BTCUSDT.BINANCE'

    backtest_strategy_runner.set_parameters(
        ab_symbols=[ab_symbol],
        interval=Interval.MINUTE,
        start=start,
        rates={
            ab_symbol: 0.0003
        },
        slippages={
            ab_symbol: 0.0000
        },
        sizes={
            ab_symbol: 1
        },
        priceticks={
            ab_symbol: 0.001
            },
        capital=10000,
        inverse={
            ab_symbol: False
            },
        end=end,
        annual_days=365,
        mode=BacktestingMode.BAR
    )
    backtest_strategy_runner.add_strategy(strategy_class=DoubleMAStrategy,
                                          strategy_name='strategy_1',
                                          ab_symbols=["XBTUSD.BITMEX"],
                                          setting={}
                                          )

    backtest_strategy_runner.run_backtest()
