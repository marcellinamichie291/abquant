import os
import sys
sys.path.append("..")
import pathlib

from abquantui.ab_ui_starter import setup_log_with_config
from abquantui.config_helpers import parse_yaml

from risk_control.liquidator import Liquidator


if __name__ == '__main__':
    parent_path = pathlib.Path(__file__).parent
    config_path = os.path.join(parent_path, 'config', 'liquidation.yaml')

    setup_log_with_config(config_path)

    config = parse_yaml(config_path)
    liq = Liquidator(config)
    liq.connect_gateway()
    liq.log(liq.status())
    liq.start()
    liq.log(liq.status())
