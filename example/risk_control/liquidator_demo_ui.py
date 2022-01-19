import os
import pathlib
import sys

sys.path.append("..")
from abquantui.ab_ui_starter import ab_ui_starter

from risk_control.liquidator import Liquidator

if __name__ == '__main__':
    parent_path = pathlib.Path(__file__).parent
    config_path = os.path.join(parent_path, 'config', 'liquidation.yaml')
    ab_ui_starter(config_path, Liquidator)
