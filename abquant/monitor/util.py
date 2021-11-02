
from logging import ERROR, WARNING, INFO, DEBUG
import logging
import logging.handlers

from logging.handlers import RotatingFileHandler

LOG_LEVEL = DEBUG


def get_formatter():
    return logging.Formatter("%(asctime)s %(levelname)s  %(name)s(%(filename)s:%(lineno)d)  %(message)s")


def get_handler(htype):
    handler = None
    if htype == 'stdout':
        handler = logging.StreamHandler()
    elif htype == 'file':
        # handler = TimedRotatingFileHandler(**config)
        handler = RotatingFileHandler("abquant.log", maxBytes=10*1024*1024, encoding="UTF-8", backupCount=10)
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(get_formatter())
    return handler


logging.basicConfig()
logger = logging.getLogger('abquant')
logger.setLevel(LOG_LEVEL)
# logger.addHandler(get_handler('stdout'))
logger.addHandler(get_handler('file'))
