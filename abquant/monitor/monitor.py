from abc import ABC, abstractmethod
from typing import Dict
import json



class Monitor(ABC):
    def __init__(self):
        self.username = None

    @abstractmethod
    def login(self, setting: Dict):
        pass

    @abstractmethod
    def send(self, info: str):
        pass

    def push_info(self, info: Dict):
        info_json = json.dumps(info)
        self.send(info_json)
        

 