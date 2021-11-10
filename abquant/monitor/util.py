import os
import logging
from logging.handlers import RotatingFileHandler
import json

LOG_LEVEL = logging.INFO
FORMAT = "%(asctime)s %(levelname)s %(message)s"


logging.basicConfig(format=FORMAT)
logger = logging.getLogger('abquant')


def get_formatter():
    return logging.Formatter(FORMAT)


def get_handler(htype, log_path):
    handler = None
    if htype == 'stdout':
        handler = logging.StreamHandler()
    elif htype == 'file':
        # handler = TimedRotatingFileHandler(**config)
        handler = RotatingFileHandler(log_path + "abquant.log", maxBytes=10*1024*1024, encoding="UTF-8", backupCount=10)
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(get_formatter())
    return handler


def config_logger(log_path=''):
    if log_path is None:
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
    global logger
    if logger is None:
        logger = logging.getLogger('abquant')
    logger.setLevel(LOG_LEVEL)
    # logger.addHandler(get_handler('stdout'))
    logger.addHandler(get_handler('file', log_path))


def print_log_format(data):
    if isinstance(data, (int, float)):
        logger.info(str(data))
    elif isinstance(data, (list, tuple, set)):
        logger.info(str(data))
    elif isinstance(data, dict):
        try:
            strategy_name = data.get("strategy_name")
            event_type = data.get("event_type")
            run_id = data.get("run_id")
            payload = data.get("payload")
            formatStr = ''
            if strategy_name is not None and strategy_name != '':
                formatStr += f'[{strategy_name}] '
            # if run_id is not None and run_id[:2] != '0x':
            #     formatStr += f'[{run_id}] '
            if payload is not None:
                if event_type == 'order':
                    formatStr += f"订单: {payload.get('exchange')} - {payload.get('symbol')} - {payload.get('direction')} status: {payload.get('status')}, price: {payload.get('price')}, volume: {payload.get('volume')}, type: {payload.get('type')}, order_id: {payload.get('orderid')} "
                elif event_type == 'order_trade':
                    formatStr += f"订单成交: {payload.get('exchange')} - {payload.get('symbol')} - {payload.get('direction')} price: {payload.get('price')}, volume: {payload.get('volume')}, order_id: {payload.get('orderid')}, trade_id: {payload.get('tradeid')} "
                elif event_type == 'position':
                    formatStr += f'仓位: {payload.get("exchange")} - {payload.get("symbol")}:  {payload.get("position")}'
                elif event_type == 'parameter':
                    formatStr += f'参数: {payload.get("name")}:  {payload.get("value")}'
                elif event_type == 'status_report':
                    ptype = payload.get("type")
                    if ptype == 'start':
                        formatStr += f'策略开始'
                    elif ptype == 'end':
                        formatStr += f'策略结束'
                    elif ptype == 'heartbeat':
                        formatStr += f'策略心跳'
                        logger.debug(formatStr)
                        return
                    else:
                        formatStr += str(ptype)
                elif event_type == 'log':
                    ltype = payload.get("type")
                    if ltype == 'system':
                        formatStr += f'系统日志: {payload.get("level")}  {payload.get("msg")}'
                    elif ltype == 'custom':
                        formatStr += f'自定义日志: {payload.get("level")}  {payload.get("msg")}'
                    else:
                        formatStr += str(payload.get("msg"))
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
