from telegram.bot import Bot
from telegram.parsemode import ParseMode
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from telegram.update import Update
from telegram.error import (
    NetworkError,
    TelegramError,
)
from telegram.ext import (
    MessageHandler,
    Filters,
    Updater,
    CallbackContext
)
import threading
from abquant.strategytrading import StrategyTemplate, LiveStrategyRunner
from abquant.event import EventDispatcher, Event

COMMONDS = {
    'status': 'status',
    'start': 'start',
    'stop': 'stop',
}



class TelegramNotifier():

    def __init__(self,
                 token: str,
                 chat_id: str,
                 proxy_ip: str,
                 proxy_port: str,
                 strategyrunner
                 ) -> None:
        super().__init__()
        self._token = token
        self._chat_id = chat_id
        if not proxy_ip is None and not proxy_port is None:
            proxy_url = 'http://{}:{}'.format(proxy_ip, proxy_port)
            self._updater = Updater(token=token, workers=1, request_kwargs={'proxy_url':'http://{}:{}'.format(proxy_ip, proxy_port)})
        else:
            self._updater = Updater(token=token, workers=1)
        self.lock = threading.Lock()
        self.stgrunner = strategyrunner
        # Register command handler and start telegram message polling
        handles = [MessageHandler(Filters.text, self.handler)]
        for handle in handles:
            self._updater.dispatcher.add_handler(handle)

    def start(self):
        self._updater.start_polling(
            drop_pending_updates=True,
            bootstrap_retries=-1,
            timeout=30,
            read_latency=60
            ,
        )
        markup = ReplyKeyboardMarkup(keyboard=[COMMONDS.keys()], resize_keyboard=True)
        self._updater.bot.sendMessage(chat_id=self._chat_id, text='策略开始启动', reply_markup=markup)
        print("Telegram is listening...")

    def handler_commond(self, commond, context):
        if not commond in COMMONDS.keys():
            return
        if self.lock.locked():
            context.bot.send_message(chat_id=self._chat_id, text="未取到锁，命令[{}]未执行".format(commond))
            return
        self.lock.acquire()
        try:
            if not hasattr(self.stgrunner, commond):
                context.bot.send_message(chat_id=self._chat_id, text='方法{}尚未支持'.format(commond))
            res = eval('self.stgrunner.' + COMMONDS.get(commond) + '()')
            if not res == None:
                context.bot.send_message(chat_id=self._chat_id, text=res)
        finally:
            self.lock.release()

    def handler(self, update: Update, context: CallbackContext) -> None:
        msg = update.message.text
        thread = threading.Thread(target=self.handler_commond, args=(msg, context))
        thread.setDaemon(True)
        thread.start()

# def main():
#     event_dispatcher = EventDispatcher(interval=1)
#     strategy_runner = LiveStrategyRunner(event_dispatcher)
#     notifier = TelegramNotifier(token='5028611800:AAGThdT7_8JOcoWpCXF_bc1nkQQusHgoC2o', chat_id=2110131695,
#                                 proxy_ip='127.0.0.1', proxy_port=1087, strategyrunner=strategy_runner)
#     notifier.start()
#
# if __name__ == '__main__':
#     main()