import time
from abquant.event import EventDispatcher, EventType
from abquant.gateway import RaydiumGateway
from abquant.trader.object import SubscribeRequest
from abquant.trader.common import Exchange

if __name__ == '__main__':
    setting = {
        "secret_key": 'I am a secret key, but if you just use the listener, you dont need to set me a value',
    }

    event_dispatcher = EventDispatcher()
    event_dispatcher.register(EventType.EVENT_TICK, lambda event: print(
        str('TICK: ') + str(event.data)))

    gateway = RaydiumGateway(event_dispatcher)
    gateway.connect(setting)

    # sleep 是等待交易所 信息与账户信息同步的必要处理。这是异步框架比较丑陋的地方。
    time.sleep(3)

    gateway.subscribe(SubscribeRequest(
        symbol='WSOLUSDC', exchange=Exchange.RAYDIUNM))

    gateway.start()
