
import logging

from logging.handlers import RotatingFileHandler

LOG_LEVEL = logging.DEBUG
FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def get_formatter():
    return logging.Formatter(FORMAT)


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


logging.basicConfig(format=FORMAT)
logger = logging.getLogger('abquant')
logger.setLevel(LOG_LEVEL)
# logger.addHandler(get_handler('stdout'))
logger.addHandler(get_handler('file'))
