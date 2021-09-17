# abquant
abquant 是内部用的纯python实现的专注于数字货币金融产品的量化交易系统，设计理念是基于事件驱动的架构。支持tick2order在毫秒级的全种类策略实现,且能保证实盘与回测的策略实现保持一致。

初期版本仅支持策略实盘，后期计划会加入回测。


# dependency and environment

开发将在python3.8以及 类unix系统中进行，建议使用时保证环境的一致性。

## python依赖库安装

```
#安装 talib，mac上可以brew install talib， linux环境自行编译安装
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
## q: binance 下单报 {"code":-4061,"msg":"Order\'s position side does not match user\'s setting."}'

a: 
请将下单中的偏好设置中的position mode 设置为 one-way mode. 不支持hedge mode的原因是，crypto不存在传统金融产品中平今平昨的概念 ，以及平昨费率低于平今的可能。而 hedge mode与one-way mode对于下单参数有不同要求，支持两者徒增api复杂度。


## q: 订阅行情失败，没接收到行情。
a: 检查。1. 监听Event.EVENT_LOG, 是否收到Event，LogData(gateway_name='BINANCEBBC', msg='交易Websocket API连接成功', level=20)。 如果没有收到则确定没有连接成功。检查网络问题，以及apikey，secret。是否在GFW 环境下，gateway 的setting参数中未设置 proxy 2. 监听Event.EVENT_LOG, 是否收到是否收到Event, LogData(gateway_name='BINANCEBBC', msg='找不到该合约代码xxxx', level=30), 则意味着在某个gateway中尝试 subscribre了 不存在的symbol。


## q: strategy.get_balance这么一个功能。为什么难于实现。

a: 

1.abquant原则是 strategy 1次 实现， 2处运行（实盘，回测）

2.两个功能需要考虑实现，strategy.get_postion, 和strategy.get_balance。

3.strategy，和gateway/账户是不同的概念。1个strategy 可以连接不同的gateway/账户. 而1个gateway/账户也可以同时运行多个strategy（在不同的进程上）。比如一个B本位策略+开空等量BTC永续的费率套利策略，就可以变成U本位策略。

4.存在如下组合关系。1strategy- 1gateway/账户，1strategy- 多gateway/账户， 多stratey-多gateway/账户， 多strategy-1gateway/账户，
5.加上 实盘与回测，就是一套api要支持8种情况，无歧义的运行。

6.先说strategy.get_postion。该功能可以直接get请求交易所获得某个gateway/账户的所有持仓。多gateway/账户的情况直接分别请求加总即可。 但多stratey的情况，不好处理。因为每个strategy是有自己的持仓的。清仓strategy1的所有持仓不需要清仓strategy2的持仓。因此strategy.get_postion 一定是每个strategy实例分别根据订单成交回报以及orderid各自维护一份position信息。实盘与回测同理。

7.再说strategy.get_balance。balance信息通常相对于gateway/账户 而言，这意味着实盘模式中1strategy的情况返回「gateway-balance」对儿即可。
而回测模式下1strategy的的情况意味着，根据每次成交实时的计算当前gateway/账户的balance。而通常的实现是在模拟撮合在历史数据上全部完成后在计算收益。模拟撮合是一个比较复杂的状态机，撮合成交后实时计算balance会增加不少的的复杂度
而对于多strategy来说，就特别tricky了。实盘显然不建议多strategy共享同一个gateway/账户的balance。但只要交易员很清楚自己在做什么那也没问题.

但多strategy的回测就太trick了。支持多strategy的回测是 abquant的一个很核心的功能。多strategy的好处不言而喻，通过收益部相关性不高的多个策略拉平总收益，也是大数定律的很好应用。通常多strategy回测的实现，是逐个strategy模拟撮合完成后再对齐时间后计算综合下来的逐日收益。 这样的实现意味着要多次回放历史数据，且最后的综合计算也有不少trick的地方容易出错。原本abquant的架构使得多strateg的一遍回放，最后计算。使得1/多strategy的回测在abquant能够通用的支持。 
但如果要支持在strategy中 相对于gateway/账户的get_balance的回测。一切就变负责了很多。

8.库的软件工程问题就是这样。特殊化都很简单，相应的根据需求写一遍代码即可。 但要做到通用（意味着api的俭省易用），就是有这些伞兵问题难以解决。api一旦提供，就必然会被乱用，因此不提供就是个相对不差的选择。


## q: 启动策略后 没有交易回报。

a: 试通过
```event_dispatcher.register(EventType.EVENT_LOG, lambda event: print(str('LOG: ') + str(event.data.time) + str(event.data))) ```
打印所有LOG事件，如果任何交易gateway的连接务必出现以下7条log， 若有确实，则为gateway连接未成功， 在启动strategy之前请先sleep一段时间，等待异步io完成。

LOG: 2021-09-14 15:32:17.404159LogData(gateway_name='BINANCEUBC', msg='REST API启动成功', level=20)
LOG: 2021-09-14 15:32:18.150155LogData(gateway_name='BINANCEUBC', msg='账户资金查询成功', level=20)
LOG: 2021-09-14 15:32:18.336595LogData(gateway_name='BINANCEUBC', msg='交易单信息查询成功', level=20)
LOG: 2021-09-14 15:32:18.631362LogData(gateway_name='BINANCEUBC', msg='持仓信息查询成功', level=20)
LOG: 2021-09-14 15:32:18.674333LogData(gateway_name='BINANCEUBC', msg='交易所支持合约信息查询成功', level=20)
LOG: 2021-09-14 15:32:19.574005LogData(gateway_name='BINANCEUBC', msg='交易Websocket API连接成功', level=20)
LOG: 2021-09-14 15:32:19.574005LogData(gateway_name='BINANCEUBC', msg='行情Websocket API', level=20)


## q:  SSLError(e, request=request)\nrequests.exceptions.SSLError: HTTPSConnectionPool(host=xxx, port=xxx): Max retries exceeded with url xxx.

a: 通常这意味着网络故障，极有可能来自于币所，也有可能来自于交易服务器的网络故障。 如果有代理服务器，有限考虑检查代理服务器网络故障。