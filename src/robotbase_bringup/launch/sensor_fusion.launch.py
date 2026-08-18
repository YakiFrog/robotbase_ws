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
    default_params = os.path.join(share, 'config', 'ekf.yaml')
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')
    tf_prefix = LaunchConfiguration('tf_prefix')
    base_frame = PathJoinSubstitution([tf_prefix, 'base_footprint'])
    odom_frame = PathJoinSubstitution([tf_prefix, 'odom'])

    configured = RewrittenYaml(
        source_file=params_file,
        root_key='',
        param_rewrites={
            'use_sim_time': use_sim_time,
            'base_link_frame': base_frame,
            'odom_frame': odom_frame,
            'world_frame': odom_frame,
        },
        convert_types=True,
    )
    parameters = ParameterFile(configured, allow_substs=True)

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('tf_prefix', default_value='robot'),
        Node(
            package='robot_localization', executable='ekf_node', name='ekf_node',
            output='screen', parameters=[parameters],
            remappings=[('/odometry/filtered', '/odom/filtered')],
        ),
    ])
