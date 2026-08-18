"""Load robot identity and runtime isolation settings from ``robot.env``."""

import re
import shlex
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = WORKSPACE / 'robot.env'


def _read_env_file(path):
    values = {}
    with path.open(encoding='utf-8') as config:
        for raw_line in config:
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            key, separator, raw_value = line.partition('=')
            if not separator:
                continue
            parts = shlex.split(raw_value, comments=True)
            values[key.strip()] = parts[0] if parts else ''
    return values


_config = _read_env_file(CONFIG_FILE)

DISPLAY_NAME = _config.get('ROBOTBASE_DISPLAY_NAME', 'ココちゃん')
ROBOT_ID = _config.get('ROBOTBASE_ID', 'koko')
ROS_DOMAIN_ID = _config.get('ROBOTBASE_ROS_DOMAIN_ID', '57')
GZ_PARTITION = _config.get('ROBOTBASE_GZ_PARTITION', ROBOT_ID)
TF_PREFIX = _config.get('ROBOTBASE_TF_PREFIX', 'robot').strip('/')

if not re.fullmatch(r'[a-z0-9_-]+', ROBOT_ID):
    raise ValueError('ROBOTBASE_ID must contain only lowercase letters, numbers, _ or -')
if not ROS_DOMAIN_ID.isdigit() or not 0 <= int(ROS_DOMAIN_ID) <= 232:
    raise ValueError('ROBOTBASE_ROS_DOMAIN_ID must be an integer from 0 to 232')
if not re.fullmatch(r'[a-zA-Z0-9_-]+', TF_PREFIX):
    raise ValueError('ROBOTBASE_TF_PREFIX must be one non-empty frame-name component')

LAUNCHER_ID = f'{ROBOT_ID}_launcher'
LAUNCHER_TITLE = f'{DISPLAY_NAME} ROS 2 Launch Manager'
TAB_PREFIX = f'[{DISPLAY_NAME}]'
ALIAS_FILE = WORKSPACE / 'bash' / 'bash_alias2.sh'
SOURCE_ALIAS = f'{ROBOT_ID}_src'
ENV_ALIAS = f'{ROBOT_ID}_env'
