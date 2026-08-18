#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('robotbase_sim')
    slam_share = get_package_share_directory('slam_toolbox')
    sim_launch = os.path.join(pkg_share, 'launch', 'sim.launch.py')
    slam_launch = os.path.join(slam_share, 'launch', 'online_async_launch.py')
    slam_params = os.path.join(pkg_share, 'config', 'slam_toolbox.yaml')
    rviz_config = os.path.join(pkg_share, 'rviz', 'robotbase.rviz')

    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')

    simulator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sim_launch),
        launch_arguments={'gui': gui}.items(),
    )
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(slam_launch),
        launch_arguments={
            'use_sim_time': 'true',
            'autostart': 'true',
            'slam_params_file': slam_params,
        }.items(),
    )
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        simulator,
        TimerAction(period=5.0, actions=[slam, rviz_node]),
    ])
