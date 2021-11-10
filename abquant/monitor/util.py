
DEBUG_LEVEL = 1
INFO_LEVEL = 2
WARNING_LEVEL = 4
ERROR_LEVEL = 5
LOG_LEVEL = DEBUG_LEVEL


class MLogger:

    @staticmethod
    def debug(data):
        if LOG_LEVEL <= DEBUG_LEVEL:
            print(data)

    @staticmethod
    def log(data):
        MLogger.debug(data)

    @staticmethod
    def info(data):
        if LOG_LEVEL <= INFO_LEVEL:
            print(data)

    @staticmethod
    def warn(data):
        if LOG_LEVEL <= WARNING_LEVEL:
            print(data)

    @staticmethod
    def error(data):
        if LOG_LEVEL <= ERROR_LEVEL:
            print(data)
