import os
import pathlib
import sys

sys.path.append("..")
from abquantui.ab_ui_starter import ab_ui_starter

from example.risk_control.liquidator import Liquidator

if __name__ == '__main__':
    parent_path = pathlib.Path(__file__).parent
    config_path = os.path.join(parent_path, 'liquidator_demo.yaml')
    ab_ui_starter(config_path, Liquidator)
