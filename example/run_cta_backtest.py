
from datetime import datetime
import time
from abquant.dataloader import DataLoaderKline
from abquant.dataloader.dataloader import DataLoader
from abquant.strategytrading import BacktestParameter, BacktestStrategyRunner, BacktestingMode
from abquant.trader.common import Interval
from strategy.doublemeanaverage import DoubleMAStrategy
# from abquant.dataloader.dfdataloader import DFDataLoader


if __name__ == '__main__':
    dl_setting = {
        "dir_path": '/Users/abakus/Desktop/projects/abquant/example_my/binance_history_data_all'
    }

    start = datetime(2021, 8, 1)
    end = datetime(2021, 9, 12)
    dataloader: DataLoader = DataLoaderKline(dl_setting)
    # dataloader: DataLoader = DFDataLoader(dl_setting)

    # dataset = dataloader.load_data('BTCUSDT.BINANCE', start, end)
    # for bar in dataset:
    #     print(bar)
    #     time.sleep(1)

    ab_symbol1 = 'BTCUSDT.BINANCE'
    ab_symbol2 = 'btcusdt.BINANCE'

    backtest_parameter = BacktestParameter(
        ab_symbols=[ab_symbol1, ab_symbol2],
        interval=Interval.MINUTE,
        rates={
            ab_symbol1: 0.0003,
            ab_symbol2: 0.001,
        },
        slippages={
            ab_symbol1: 0.0000,
            ab_symbol2: 0.0000,
        },
        sizes={
            ab_symbol1: 1,
            ab_symbol2: 1,
        },
        priceticks={
            ab_symbol1: 0.01,
            ab_symbol1: 0.01,
        },
        capital=200000,
        inverses={
            ab_symbol1: False,
            ab_symbol1: False
        },
        annual_days=365,
        mode=BacktestingMode.BAR
    )
    backtest_strategy_runner = BacktestStrategyRunner()
    backtest_strategy_runner.set_data_loader(dataloader)
    backtest_strategy_runner.set_parameter(backtest_parameter)

    backtest_strategy_runner.add_strategy(strategy_class=DoubleMAStrategy,
                                          strategy_name='strategy_1',
                                          ab_symbols=[ab_symbol1],
                                          setting={}
                                          )

    backtest_strategy_runner.run_backtest(start_dt=start, end_dt=end, output_log=True)
