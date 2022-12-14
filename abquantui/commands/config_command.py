from typing import TYPE_CHECKING, Dict
import json

from abquantui.config_helpers import parse_config, yaml

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class ConfigCommand:

    def config(self: "AbquantApplication", subcommand, key, value):
        if not subcommand:
            self._notify(self.strategy_lifecycle.command_config())
        if 'update' == subcommand:
            self.config_update(key, value)

        elif 'reload' == subcommand:
            self.config_reload()

        elif 'yaml' == subcommand:
            self._notify(self.strategy_lifecycle.command_config(True))
        # self._notify(f'{subcommand} {key} {value}')
        # self._notify('\nconfig_path: {}'.format(self.config_path))
        # self._notify('\n' + self.strategy_lifecycle.config())

    def config_reload(self: "AbquantApplication"):
        self._config: Dict = parse_config(self.config_path)
        self.strategy_lifecycle.config = self._config
        self._notify('config reload success')
        self._notify(self.strategy_lifecycle.command_config())

    def config_update(self: "AbquantApplication", key, value):
        if key is not None and key in self._config.get('params', {}):
            if value:
                orig_type = type(self._config['params'][key])
                try:
                    value = orig_type(value)
                except Exception as e:
                    if orig_type == int and value.strip('- ').replace('.', '').isdecimal():
                        value = float(value)
                    else:
                        self._notify(str(e))
                        return
                self._config['params'][key] = value
                with open(self.config_path, 'w') as f:
                    cpath = str(self.config_path)
                    if cpath.split('.')[-1] == 'yml' or cpath.split('.')[-1] == 'yaml':
                        yaml.dump(self._config, f)
                    elif cpath.split('.')[-1] == 'json':
                        json.dump(self._config, f, sort_keys = False, indent = 2, separators=(',', ': '))

                self._notify('config update success -> params.{} = {}'.format(key, value))
            else:
                self._notify('Usage: config update key value, update failed -> value is None')
        else:
            self._notify(f'Usage: config update key value, can not find key {key} in params, update failed')
