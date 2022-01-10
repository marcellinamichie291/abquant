
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
        # "dir_path": '/Users/abakus/Desktop/projects/abquant/example_my/binance_history_data_all'
        "aws_access_key_id": "AKIA5U5U7HQ2PGYMOU46",
        "aws_secret_access_key": "tXEGX04SCAXy3J/qDNgr+pvk3+rpz8I9tF+1+kFG",
    }

    start = datetime(2021, 8, 1)
    end = datetime(2021, 10, 1)
    dataloader: DataLoader = DataLoaderKline(dl_setting)

    # dataset1 = dataloader.load_data('BTCUSDT.BINANCE', start, end)
    # dataset2 = dataloader.load_data('btcusdt.BINANCE', start, end)
    # for bar1, bar2 in zip(dataset1, dataset2):
    #     if bar1.datetime != bar2.datetime:
    #         print(bar1)
    #         print(bar2)
    #         time.sleep(1)

    # 合约
    ab_symbol1 = 'BTCUSDT.BINANCE'
    # 现货
    ab_symbol2 = 'ETHUSDT.BINANCE'

    backtest_parameter = BacktestParameter(
        ab_symbols=[ab_symbol1, ab_symbol2],
        interval=Interval.MINUTE,
        # 费率
        rates={
            ab_symbol1: 0.0003,
            ab_symbol2: 0.001,
        },
        # 滑点
        slippages={
            ab_symbol1: 0.0000,
            ab_symbol2: 0.0000,
        },
        # 张/手
        sizes={
            ab_symbol1: 1,
            ab_symbol2: 1,
        },
        # 最小价格变化
        priceticks={
            ab_symbol1: 0.01,
            ab_symbol2: 0.01,
        },
        capital=200000,
        # 反向合约。 正向合约可以支持多产品，反向合约只能支持一个产品(处于计算收益的原因)
        inverses={
            ab_symbol1: False,
            ab_symbol2: False
        },
        annual_days=365,
        mode=BacktestingMode.BAR
    )
    backtest_strategy_runner = BacktestStrategyRunner()
    # 两项必备的前置工作， 设置dataloader + 设置参数
    backtest_strategy_runner.set_data_loader(dataloader)
    backtest_strategy_runner.set_parameter(backtest_parameter)

    # 添加策略实例 未来可支持添加多个策略实例。 最终获得每个策略实例的收益 + 所有策略实例构成的portofolio收益。
    backtest_strategy_runner.add_strategy(strategy_class=DoubleMAStrategy,
                                          strategy_name='strategy_1',
                                          ab_symbols=[ab_symbol1],
                                          setting={}
                                          )

    # output_log 代表是否 输出 策略本身的日志。
    backtest_strategy_runner.run_backtest(start_dt=start, end_dt=end, output_log=False)
