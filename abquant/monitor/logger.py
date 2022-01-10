import os
import logging
from logging.handlers import TimedRotatingFileHandler
import json
from datetime import datetime

LOG_LEVEL = logging.INFO
FORMAT = "%(message)s"

# logging.basicConfig(format=FORMAT)
# logger = logging.getLogger('abquant')


class Logger:
    def __init__(self, name="monitor"):
        # print(f"Logger {name} init")
        self._logger = logging.getLogger(name)
        self._logger.setLevel(LOG_LEVEL)
        self.config_logger()

    def get_logger(self):
        return self._logger

    def get_formatter(self):
        return logging.Formatter(FORMAT)

    def get_handler(self, htype, log_path):
        handler = None
        if htype == 'stdout':
            handler = logging.StreamHandler()
        elif htype == 'file':
            handler = TimedRotatingFileHandler(log_path + "abquant.log", when="D", encoding="UTF-8", backupCount=30)
        handler.setLevel(LOG_LEVEL)
        handler.setFormatter(self.get_formatter())
        return handler

    def config_logger(self, log_path=''):
        logger2 = self._logger
        if logger2 is None:
            logger2 = logging.getLogger('abquant')
        if log_path is None or len(log_path) == 0:
            log_path = os.getcwd() + "/logs/"
        elif log_path[-1:] != "/":
            log_path += "/"
        fret = os.access(log_path, os.F_OK)
        if not fret:
            print("log_path not exist, create")
            try:
                os.makedirs(log_path)
            except Exception as e:
                print(e)
                return
        wret = os.access(log_path, os.W_OK)
        if not wret:
            print("log_path cannot write")
            return
        # global logger
        # logger.setLevel(LOG_LEVEL)
        # logger.addHandler(get_handler('stdout'))
        logger2.addHandler(self.get_handler('file', log_path))

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def log(self, msg, *args, **kwargs):
        self.debug(msg, *args, **kwargs)

    def print(self, msg, *args, **kwargs):
        self.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def print_log_format(self, data):
        logger2 = self._logger
        if isinstance(data, (int, float)):
            logger2.info(str(data))
        elif isinstance(data, (list, tuple, set)):
            logger2.info(str(data))
        elif isinstance(data, dict):
            try:
                strategy_name = data.get("strategy_name")
                event_type = data.get("event_type")
                event_time = data.get("event_time")
                # run_id = data.get("run_id")
                payload = data.get("payload")
                if strategy_name is None and event_type is None and payload is None:
                    logger2.info(json.dumps(data))
                    return
                if event_time is not None:
                    date_array = datetime.fromtimestamp(event_time)
                else:
                    date_array = datetime.today()
                event_time = date_array.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                formatStr = f'{event_time} '
                if strategy_name is not None and strategy_name != '':
                    formatStr += f'[{strategy_name}] '
                # if run_id is not None and run_id[:2] != '0x':
                #     formatStr += f'[{run_id}] '
                if payload is not None:
                    if event_type == 'order':
                        if payload.get('datetime') is None:
                            formatStr += f"ORDER: {payload.get('exchange')} - {payload.get('symbol')} - {payload.get('direction')} ts: {event_time}, status: {payload.get('status')}, price: {payload.get('price')}, volume: {payload.get('volume')}, type: {payload.get('type')}, order_id: {payload.get('orderid')} "
                        else:
                            formatStr += f"ORDER: {payload.get('exchange')} - {payload.get('symbol')} - {payload.get('direction')} ts: {payload.get('datetime')}, status: {payload.get('status')}, price: {payload.get('price')}, volume: {payload.get('volume')}, type: {payload.get('type')}, order_id: {payload.get('orderid')} "
                    elif event_type == 'order_trade':
                        if payload.get('datetime') is None:
                            formatStr += f"TRADE: {payload.get('exchange')} - {payload.get('symbol')} - {payload.get('direction')} ts: {event_time}, price: {payload.get('price')}, volume: {payload.get('volume')}, order_id: {payload.get('orderid')}, trade_id: {payload.get('tradeid')} "
                        else:
                            formatStr += f"TRADE: {payload.get('exchange')} - {payload.get('symbol')} - {payload.get('direction')} ts: {payload.get('datetime')}, price: {payload.get('price')}, volume: {payload.get('volume')}, order_id: {payload.get('orderid')}, trade_id: {payload.get('tradeid')} "
                    elif event_type == 'position':
                        formatStr += f'POSITION: {payload.get("exchange")} - {payload.get("symbol")}:  {payload.get("position")}'
                    elif event_type == 'parameter':
                        formatStr += f'PARAMETER: {payload.get("name")}:  {payload.get("value")}'
                    elif event_type == 'status_report':
                        ptype = payload.get("type")
                        if ptype == 'start':
                            formatStr += f'Strategy Start'
                        elif ptype == 'end':
                            formatStr += f'Strategy End'
                        elif ptype == 'heartbeat':
                            formatStr += f'Strategy Heartbeat'
                        else:
                            formatStr += str(ptype)
                        logger2.debug(formatStr)
                        return
                    elif event_type == 'log':
                        gateway_name = data.get("gateway_name")
                        if gateway_name is not None:
                            formatStr += f'[{gateway_name}] '
                        ltype = payload.get("type")
                        if ltype == 'system':
                            formatStr += f'SYSTEM LOG: {payload.get("level")} {payload.get("msg")}'
                        elif ltype == 'custom':
                            formatStr += f'CUSTOM LOG: {payload.get("level")} {payload.get("msg")}'
                        else:
                            formatStr += str(payload.get("msg"))
                    elif event_type == 'lark':
                        formatStr += f'SEND LARK: {payload.get("message")}'
                    else:
                        formatStr += json.dumps(payload)
                else:
                    formatStr += f'{event_type} '
                logger2.info(formatStr)
            except Exception as e:
                logger2.error(e)
        else:
            logger2.info(str(data))
        pass

