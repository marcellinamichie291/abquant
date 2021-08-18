import sys
import traceback
from enum import Enum, IntEnum, auto
from typing import Any, Callable, Optional, Union, Type
from abc import ABC, abstractmethod


import requests


class RequestStatus(IntEnum):

    ready = auto()      # Request created
    success = auto()     # Request successful (status code 2xx)
    failed = auto()      # Request failed (status code not 2xx)
    error = auto()       # Exception raised


class Request:

    def __init__(
        self,
        method: str,
        path: str,
        params: dict,
        data: Union[dict, str, bytes],
        headers: dict,
        callback: Callable = None,
        on_failed: Callable = None,
        on_error: Callable = None,
    ):
        """"""
        self.method: str = method
        self.path: str = path
        self.callback  = callback
        self.params: dict = params
        self.data: Union[dict, str, bytes] = data
        self.headers: dict = headers

        self.on_failed = on_failed
        self.on_error  = on_error

        self.response: requests.Response = None
        self.status: RequestStatus = RequestStatus.ready

    def __str__(self):
        """"""
        if self.response is None:
            status_code = "terminated"
        else:
            status_code = self.response.status_code

        return (
            "request : {} {}  because {}: \n"
            "headers: {}\n"
            "params: {}\n"
            "data: {}\n"
            "response:"
            "{}\n".format(
                self.method,
                self.path,
                status_code,
                self.headers,
                self.params,
                self.data,
                "" if self.response is None else self.response.text,
            )
        )
