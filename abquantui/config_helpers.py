import os
from io import StringIO
from pathlib import Path, PosixPath
from typing import Dict
import json5
from ruamel.yaml import YAML
import logging, logging.config


yaml = YAML()


def parse_config(config_path: str):
    config_path = str(config_path)
    with open(config_path, encoding='utf-8') as f:
        fstr = f.read().strip()
        if not config_path or not fstr:
            return None
        if (config_path.split('.')[-1] == 'yml' or config_path.split('.')[-1] == 'yaml') and fstr[0] not in ('{', '['):
            return yaml.load(fstr)
        elif config_path.split('.')[-1] == 'json' and fstr[0] == '{':
            return json5.loads(fstr)
        else:
            logging.info('Config parse fail')
            return None

def parse_yaml(config_path: str):
    return parse_config(config_path)


def json_config_to_str(config: Dict, sort_keys = False, indent = 2, separators=(',', ': ')):
    return json5.dumps(config, sort_keys=sort_keys, indent=indent, separators=separators)


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
