import os
import logging
from logging.handlers import RotatingFileHandler

LOG_LEVEL = logging.DEBUG
FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


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

