

## 0.7.0
1. 回测部分dataloader基本完成，但接口尚未完成，支持本地csv和远程aws s3
1. 更新monitor的logger
1. 增加lark notifer模块

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
