## 0.8.3
1. dataloader修正输出bardata格式
1. 处理多线程中的load_data和remoteloader

## 0.8.2
1. binances 配置项默认值处理
1. binainces 支持市价单。

## 0.8.1
1. 新增bybit B本位 gateway.
1. bybit支持subscribe_mode。 可任意订阅5类行情。

## 0.8.0
1. 去掉monitor在连接服务器时多余的错误日志
1. monitor停止上传日志到websocket服务器
1. 新增bybit U本位 gateway。（注意， 由于bybit目前不支持单向持仓。因此必须非常审慎的使用 strategyTemplate.pos对象，最好在策略中自行维护双向的仓位。该对象维护的是净持仓。同时send_order中要非常明确的使用Offset.Close 来平掉某一方向的仓位。）

## 0.7.4
1. base virtual matcher OrderBook class
1. 回测api固定
1. 监测用 rawdata in binancec gateway

## 0.7.3
1. data loader kline 缓存位置修复
1. livestrategyrunner load_bars更友好的报错信息。
1. 新增 双均线杨利策略。方便回测和参考使用。
1. run_cta_backtest.py 回测使用样例。 

## 0.7.2
1. data loader kline子类实现与接口一致
1. data loader本地csv暂不检查
1. binancec 10s ratelimit 相当复杂的并发+异步回调构成的 ratelimit bug，基本解决，偶有漏限。

## 0.7.1
1. binancec 10s ratelimit 保守重置机制, 锁保护(无测试环境，待验证。)
1. bargenerator, 0tick情况时 bar 生成。

## 0.7.0
1. 回测部分dataloader基本完成，但接口尚未完成，支持本地csv和远程aws s3
1. 更新monitor的logger
1. 增加 monitor的 直接向lark发送信息的功能。

## 0.6.3
1. 处理event handler中有可能异常的问题。
1. KlineDataLoader 部分实现。


## 0.6.2
1. 处理无行情产品barData聚合问题。

## 0.6.1
1. telegramNotifer 初版
1. binancecgateway request limit on query_history
1. bitmexgateway request limit on query_history
1. dydx增加post only, 增加一些币种常量

## 0.6.0
1. dydx 重构
1. binancec，bitmex POSTONLYLIMIT订单支持
1. binancec，订单回报bug修复
1. EVENT_RAW 增加，方便处理账户监听。
1. 回测准备，重构StrategyRunner
1. 内存泄漏问题修复。
1. bitmex on_raw 修复。
