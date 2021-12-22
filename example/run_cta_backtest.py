
from datetime import datetime
import time
from abquant.dataloader import DataLoaderKline
from abquant.dataloader.dataloader import DataLoader
from abquant.strategytrading import BacktestParameter, BacktestStrategyRunner, BacktestingMode
from abquant.trader.common import Interval
from strategy.doublemeanaverage import DoubleMAStrategy


from abquant.dataloader.dfdataloader import DFDataLoader
if __name__ == '__main__':
    dl_setting = {
        "dir_path": '/Users/abakus/Desktop/projects/abquant/example_my/binance_history_data_all'
    }

    start = datetime(2021, 8, 1)
    end = datetime(2021, 9, 12)
    dataloader: DataLoaderKline = DataLoaderKline(dl_setting)
    # dataset = dataloader.load_data('BTCUSDT.BINANCE', start, end)
    # for bar in dataset:
    #     print(bar)
    #     time.sleep(1)

    ab_symbol = 'BTCUSDT.BINANCE'

    backtest_parameter = BacktestParameter(
        ab_symbols=[ab_symbol],
        interval=Interval.MINUTE,
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
        capital=200000,
        inverses={
            ab_symbol: False
        },
        annual_days=365,
        mode=BacktestingMode.BAR
    )
    backtest_strategy_runner = BacktestStrategyRunner()
    backtest_strategy_runner.set_data_loader(dataloader)
    backtest_strategy_runner.set_parameter(backtest_parameter)

    backtest_strategy_runner.add_strategy(strategy_class=DoubleMAStrategy,
                                          strategy_name='strategy_1',
                                          ab_symbols=[ab_symbol],
                                          setting={}
                                          )

    backtest_strategy_runner.run_backtest(start_dt=start, end_dt=end, output_log=True)
