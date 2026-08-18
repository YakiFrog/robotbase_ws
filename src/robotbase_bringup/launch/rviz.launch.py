#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from nav2_common.launch import ReplaceString


def generate_launch_description():
    share = get_package_share_directory('robotbase_bringup')
    urdf_path = os.path.join(share, 'urdf', 'robotbase.urdf')
    rviz_template = os.path.join(share, 'rviz', 'robotbase.rviz')
    with open(urdf_path, 'r', encoding='utf-8') as urdf_file:
        robot_description = urdf_file.read()

    use_sim_time = LaunchConfiguration('use_sim_time')
    publish_description = LaunchConfiguration('publish_description')
    tf_prefix = LaunchConfiguration('tf_prefix')
    frame_prefix = PythonExpression(["'", tf_prefix, "/'"])
    rviz_path = ReplaceString(
        source_file=rviz_template,
        replacements={'TF_PREFIX': tf_prefix},
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument(
            'publish_description', default_value='true',
            description='Publish the robot URDF. Set false when the simulator already does it.'),
        DeclareLaunchArgument('tf_prefix', default_value='robot'),
        Node(
            package='robot_state_publisher', executable='robot_state_publisher',
            name='robotbase_state_publisher', output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'robot_description': robot_description,
                'frame_prefix': frame_prefix,
            }],
            condition=IfCondition(publish_description),
        ),
        Node(
            package='rviz2', executable='rviz2', name='koko_rviz',
            output='screen', arguments=['-d', rviz_path],
            parameters=[{'use_sim_time': use_sim_time}],
        ),
    ])
