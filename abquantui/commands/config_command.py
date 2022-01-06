from typing import TYPE_CHECKING
from abquantui.config_helpers import yaml_config_to_str

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class ConfigCommand:

    def config(self: "AbquantApplication"):
        self._notify('\nconfig_path: {}'.format(self.config_path))
        self._notify('\n' + self.strategy_lifecycle.config())

