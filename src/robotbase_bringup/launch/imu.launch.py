#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    share = get_package_share_directory('robotbase_bringup')
    default_params = os.path.join(share, 'config', 'imu.yaml')
    tf_prefix = LaunchConfiguration('tf_prefix')
    params_file = LaunchConfiguration('params_file')
    imu_frame = PathJoinSubstitution([tf_prefix, 'imu_link'])
    configured = RewrittenYaml(
        source_file=params_file,
        root_key='',
        param_rewrites={'frame_id': imu_frame},
        convert_types=True,
    )
    parameters = ParameterFile(configured, allow_substs=True)

    return LaunchDescription([
        DeclareLaunchArgument('tf_prefix', default_value='robot'),
        DeclareLaunchArgument('params_file', default_value=default_params),
        Node(
            package='witmotion_ros', executable='witmotion_ros_node',
            name='witmotion', output='screen', parameters=[parameters],
        ),
    ])
