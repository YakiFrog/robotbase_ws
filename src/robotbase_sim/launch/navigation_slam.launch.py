#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    sim_share = get_package_share_directory('robotbase_sim')
    bringup_share = get_package_share_directory('robotbase_bringup')
    tf_prefix = LaunchConfiguration('tf_prefix')

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_share, 'launch', 'mapping.launch.py')),
        launch_arguments={'tf_prefix': tf_prefix}.items(),
    )
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'nav2.launch.py')),
        launch_arguments={
            'use_sim_time': 'true',
            'localization': 'slam',
            'tf_prefix': tf_prefix,
            'odom_topic': '/odom',
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('tf_prefix', default_value='robot'),
        slam,
        nav2,
    ])
