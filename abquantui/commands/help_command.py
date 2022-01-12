from typing import TYPE_CHECKING
from abquantui.config_helpers import yaml_config_to_str

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication
HEADER = """

Welcome to Abquant, wish you Good Luck!

"""

HELP_TEXT = '''
Useful Commands:
- connect   connect to gateway, and then call add_init_strategy()
- config    get current config info
    - config reload  reload config file
    - config update key value  update config with key and value
- start     start the strategy
- stop      stop the strategy
- status    
- shutdown  Caution! equals kill -9 , double click ctrl+c  
- help      get help info
'''

HEADER = HEADER + HELP_TEXT

class HelpCommand:

    def help(self: "AbquantApplication"):

        self._notify(HELP_TEXT)

