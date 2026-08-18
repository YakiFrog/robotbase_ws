#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('robotbase_bringup')
    config = os.path.join(share, 'config', 'twist_mux.yaml')
    return LaunchDescription([
        Node(
            package='twist_mux', executable='twist_mux', name='twist_mux',
            output='screen', parameters=[config],
            remappings=[('cmd_vel_out', '/cmd_vel')],
        ),
    ])
