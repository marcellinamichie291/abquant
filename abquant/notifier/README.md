## telegram机器人对接流程
- 手机下载telegram https://telegram.org/
- 给自己的账号添加一个机器人 https://core.telegram.org/bots#3-how-do-i-create-a-bot
- 获取机器人的token:在BotFather聊天框中通过"API Token"命令获取
- 获取自己的会话id:在userinfobot聊天框中通过/start命令获取
- 安装telegram python模块 pip install python-telegram-bot --upgrade
- 在策略启动参数中通过-tt配置机器人的Api Token, 通过-tc配置会话ID

## 在脚本中添加telegram机器人
```python
from abquant.notifier.telegramnotifier import TelegramNotifier
    TelegramNotifier(token=args.tb_token, chat_id=args.tb_chatid, proxy_ip=args.proxy_host,
                     proxy_port=args.proxy_port, strategyrunner=strategy_runner).start()
```

## 完成策略的机器人实现
目前机器人提供了3个命令[status, start, stop]
在策略中重写status,start,stop方法。