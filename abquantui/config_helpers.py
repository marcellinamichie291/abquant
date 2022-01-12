import os
from io import StringIO
from pathlib import Path
from typing import Dict

from ruamel.yaml import YAML
import logging, logging.config

yaml = YAML()


def parse_yaml(config_path: str):
    with open(config_path, encoding='utf-8') as f:
        str = f.read()
        return yaml.load(str)

def yaml_config_to_str(config: Dict):
    stream = StringIO()
    yaml.dump(config, stream)
    return stream.getvalue()


def _get_logging_config_from_template(log_file_name):
    ppath = Path(__file__).resolve().parent
    template_path = os.path.join(ppath, 'logging_template.yaml')
    with open(template_path, encoding='utf-8') as f:
        tmp_str = f.read()
        return tmp_str.replace('{dest_filename}', log_file_name)


def setup_logging(log_file_name: str):
    log_config = None
    try:
        log_config = yaml.load(_get_logging_config_from_template(log_file_name))
    except Exception as e:
        logging.exception('', e)
    if log_config:
        logging.config.dictConfig(log_config)
    else:
        logging.basicConfig(level=logging.INFO)


if __name__ == '__main__':
    setup_logging('test')
