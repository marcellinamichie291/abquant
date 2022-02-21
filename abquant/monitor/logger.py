import os
import logging
from logging.handlers import TimedRotatingFileHandler
import json
from datetime import datetime

LOG_LEVEL = logging.INFO
FORMAT = "%(message)s"


class Logger:
    def __init__(self, name="abquant", log_path="./logs/", strategy=None, disable_logger=False):
        self._logger = logging.getLogger(name)
        self.config_logger(log_path, disable_logger)
        self._logger_struct = logging.getLogger('monitor_struct_9527')
        self.config_logger_struct(log_path, strategy)

    def get_logger(self):
        return self._logger

    def get_formatter(self):
        return logging.Formatter(FORMAT)

    def get_handler(self, htype, log_file = None, level = LOG_LEVEL):
        handler = None
        if htype == 'stdout':
            handler = logging.StreamHandler()
        elif htype == 'file':
            handler = TimedRotatingFileHandler(log_file, when="D", encoding="UTF-8", backupCount=30)
        else:
            return handler
        handler.setLevel(level)
        handler.setFormatter(self.get_formatter())
        return handler

    def config_logger(self, log_path = None, disable_logger = False):
        if not self._logger:
            return
        if not log_path:
            log_path = os.getcwd() + "/logs/"
        fret = os.access(log_path, os.F_OK)
        if not fret:
            print("log_path not exist, create")
            try:
                os.makedirs(log_path)
            except Exception as e:
                print(e)
                return
        # do not check write privilege, just throw exception
        # wret = os.access(log_path, os.W_OK)
        # if not wret:
        #     print("log_path cannot write")
        #     return
        if disable_logger:
            return
        self._logger.setLevel(LOG_LEVEL)
        self._logger.addHandler(self.get_handler('file', os.path.join(log_path, 'abquant.log')))

    def config_logger_struct(self, log_path = None, strategy: str = None):
        if not self._logger_struct:
            return
        if not log_path:
            log_path = os.getcwd() + "/logs/"
        if not strategy:
            filetrunk = 'abquant'
        else:
            filetrunk = strategy.replace(' ', '_')
        self._logger_struct.setLevel(LOG_LEVEL)
        self._logger_struct.addHandler(self.get_handler('file', os.path.join(log_path, filetrunk + '.struct')))
        self._logger_struct.propagate = False

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def log(self, msg, *args, **kwargs):
        self.debug(msg, *args, **kwargs)

    def print(self, msg, *args, **kwargs):
        self.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def info_struct(self, msg, *args, **kwargs):
        self._logger_struct.info(msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def print_log_format(self, data):
        logger = self._logger
        logger_struct = self._logger_struct
        if isinstance(data, (int, float)):
            logger.info(str(data))
        elif isinstance(data, (list, tuple, set)):
            logger.info(str(data))
        elif isinstance(data, dict):
            try:
                strategy_name = data.get("strategy_name")
                event_type = data.get("event_type")
                event_time = data.get("event_time")
                payload = data.get("payload")
                if event_type and event_type == "struct":
                    logger_struct.info(json.dumps(data))
                    return
                if strategy_name is None and event_type is None and payload is None:
                    logger.info(json.dumps(data))
                    return
                if event_time is not None:
                    date_array = datetime.fromtimestamp(event_time)
                else:
                    date_array = datetime.today()
                event_time = date_array.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                formatStr = f'{event_time} '
                if strategy_name is not None and strategy_name != '':
                    formatStr += f'[{strategy_name}] '
                if payload is not None:
                    if event_type == 'order':
                        if payload.get('datetime') is None:
                            formatStr += f"ORDER: {payload.get('gateway_name')} - {payload.get('symbol')} - {payload.get('direction')} ts: {event_time}, status: {payload.get('status')}, price: {payload.get('price')}, volume: {payload.get('volume')}, type: {payload.get('type')}, order_id: {payload.get('orderid')} "
                        else:
                            formatStr += f"ORDER: {payload.get('gateway_name')} - {payload.get('symbol')} - {payload.get('direction')} ts: {payload.get('datetime')}, status: {payload.get('status')}, price: {payload.get('price')}, volume: {payload.get('volume')}, type: {payload.get('type')}, order_id: {payload.get('orderid')} "
                    elif event_type == 'order_trade':
                        if payload.get('datetime') is None:
                            formatStr += f"TRADE: {payload.get('gateway_name')} - {payload.get('symbol')} - {payload.get('direction')} ts: {event_time}, price: {payload.get('price')}, volume: {payload.get('volume')}, order_id: {payload.get('orderid')}, trade_id: {payload.get('tradeid')} "
                        else:
                            formatStr += f"TRADE: {payload.get('gateway_name')} - {payload.get('symbol')} - {payload.get('direction')} ts: {payload.get('datetime')}, price: {payload.get('price')}, volume: {payload.get('volume')}, order_id: {payload.get('orderid')}, trade_id: {payload.get('tradeid')} "
                    elif event_type == 'position':
                        formatStr += f'POSITION: {payload.get("gateway_name")} - {payload.get("symbol")}:  {payload.get("position")}'
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
                        logger.debug(formatStr)
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
                logger.info(formatStr)
            except Exception as e:
                logger.error(e)
        else:
            logger.info(str(data))
        pass

