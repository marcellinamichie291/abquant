# abquant
abquant 是内部用的纯python实现的专注于数字货币金融产品的量化交易系统，设计理念是基于事件驱动的架构。支持tick2order在毫秒级以内的全种类策略。

初期版本仅支持策略实盘，后期计划会加入回测。

# dependency and environment

开发将在python3.8以及 类unix系统中进行，建议使用时保证环境的一致性。

## python依赖库安装

```
pip install -r requirement.txt
```

## abquant库安装(后续支持)
```
https://git.wecash.net/dct/abquant
cd abquant
pip install .
```
# strategy example

策略样例将在 abquant/example 目录下。后续会逐步更新运行脚本。