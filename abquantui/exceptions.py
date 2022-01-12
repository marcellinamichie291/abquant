"""
Exceptions used in the Hummingbot codebase.
"""


class AbquantBaseException(Exception):
    """
    Most errors raised in Hummingbot should inherit this class so we can
    differentiate them from errors that come from dependencies.
    """


class ArgumentParserError(AbquantBaseException):
    """
    Unable to parse a command (like start, stop, etc) from the hummingbot client
    """


class OracleRateUnavailable(AbquantBaseException):
    """
    Asset value from third party is unavailable
    """
