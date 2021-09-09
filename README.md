# abquant
abquant 是内部用的纯python实现的专注于数字货币金融产品的量化交易系统，设计理念是基于事件驱动的架构。支持tick2order在毫秒级的全种类策略实现,且能保证实盘与回测的策略实现保持一致。

初期版本仅支持策略实盘，后期计划会加入回测。


# dependency and environment

开发将在python3.8以及 类unix系统中进行，建议使用时保证环境的一致性。

## python依赖库安装

```
pip install -r requirement.txt
```

## abquant库安装(已支持)
```
git clone https://git.wecash.net/dct/abquant
cd abquant
pip install .
```
# strategy example

策略样例将在 abquant/example 目录下。后续会逐步更新运行脚本。



# QA
q: binance 下单报 {"code":-4061,"msg":"Order\'s position side does not match user\'s setting."}'

a: 请将下单中的偏好设置中的position mode 设置为 one-way mode. 不支持hedge mode的原因是，crypto不存在传统金融产品中平今平昨的概念 ，以及平昨费率低于平今的可能。而 hedge mode与one-way mode对于下单参数有不同要求，支持两者徒增api复杂度。

