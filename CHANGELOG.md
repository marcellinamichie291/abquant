## 1.1.4
1. abquantUI隐藏真实apikey
1. abquant_ui增加FTX
1. FTX websocket时间戳bug

## 1.1.3
1. exchange operation双向持仓debug

## 1.1.2
1. exchange operation支持双向持仓

## 1.1.1
1. abquantui status live

## 1.1.0
1. 新增 FTX 交易所支持

## 1.0.12
1. notify_lark增加消息类型,卡片消息-markdown

## 1.0.11
1. 新增bitmex订单类型STOP_MARKET
1. 修正exchange operation本地proxy问题
1. 增加exchange operation验证key有效性

## 1.0.10
1. 新增binancec cancel_all_orders(self, ab_symbol)用。

## 1.0.9
1. 更改exchange operation的GatewayName类型
1. 修正exchange operation在bitmex拒单原因
1. 修复币安币本位仓位rest api地址bug
1. 删除bybit流动性贡献分查询

## 1.0.8
1. 更新回测加载s3凭证
1. 增加exchange operation撤销订单接口

## 1.0.7
1. binance 双向持仓。
1. bybit 增加lcp查询

## 1.0.6
1. 增加exchange operation发送订单并检查交易所返回的接口

## 1.0.5
1. 增加交易所拒单的详细信息
1. 增加exchange operation订单回调处理

## 1.0.4
1. 回测订单类型报错缺失问题修复。
1. 增加exchange operation解析key函数

## 1.0.3
1. 调整abquantui结构，抽取公共对象
1. 修复exchange operation多个gateway问题

## 1.0.2
1. update bitmex websocet api.
1. dummy monitor bug fixed.

## 1.0.1
1. 添加exchange辅助操作类

## 1.0.0
1. 扩展monitor结构化日志类型
1. protofolio 多策略回测。

## 0.10.9
1. 添加monitor结构化日志
1. 添加bitmex websocket on raw提醒

## 0.10.8
1. 调整encryption内部转换编码
1. 更新run strategy with config 样例

## 0.10.7
1. readme &demo 修改
1. dataloader refine.

## 0.10.6
1. 增加run strategy with config 样例
1. 增加run strategy with ui 样例
1. monitor 增加调试用接口
1. bybit增加仓位强平价格, 修复币本位下单量bug, 币本位双向持仓仓位bug 
1. binance合约增加STOP_MARKET订单, 用于提前挂止损单
1. dataloader增加从clickhouse数据库加载行情

## 0.10.5
1. binance monitor测时精确
1. binance ratelimiter，对cancel技术orderlimit fixed。 log补充。
1. encryptool 小改。

## 0.10.4
1. monitor logger 重构
1. aes 秘钥加密解密工具，并集成到abquantui中
1. abquant回测 数值溢出warning
1. 多产品gateway断联+1分钟导致的bargenerate可能的错误修复
1. 长数据预热情况支持

## 0.10.3
1. bybit 增加on_raw 处理仓位，账户和挂单的监控。
1. binance 检测请求耗时监控。
1. raw事件 readme
1. abquant ui 简化启动代码

## 0.10.2
1. 样例与BarGenerator入参提示修改。
1. abquantui 支持bybit

## 0.10.1
1. dydx订单回报丢失,增加restful查询
1. bybit best tick bug修复

## 0.10.0
1. abquant 回测登场。
1. 目前支持多金融产品，分钟级回测，后续会推出多策略回测。（请注意阅读readme，有一些新依赖需要安装，以及回测的使用样例）
1. 回测目前仅支持binance， 数据自2021.7月起，且binance提供的历史现货数据似乎有小概率丢失的情况。数据的完整性后续会陆续补足。
1. bybit监控所需的on_raw数据。

## 0.9.2
1. abquantui增加异常
1. abquantui config 命令列出配置项， reload子命令加载配置文件
1. abquantui config update key value 实时修改配置， 并回写至配置文件

## 0.9.1
1. 修改aws s3认证方式, 与配置setting
1. 修复dataloader，加载现货的的大小写问题。

## 0.9.0
1. abquantui 横空出炉, 提供命令行交互的用户界面。
1. dataloader线程安全。
1. dataloader选取数据精确到分钟。

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
