#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    pkg_share = get_package_share_directory('robotbase_sim')
    nav2_share = get_package_share_directory('nav2_bringup')
    sim_launch = os.path.join(pkg_share, 'launch', 'sim.launch.py')
    nav2_launch = os.path.join(nav2_share, 'launch', 'navigation_launch.py')
    default_params = os.path.join(nav2_share, 'params', 'nav2_params.yaml')
    default_map = os.path.join(pkg_share, 'maps', 'test_arena.yaml')
    rviz_config = os.path.join(pkg_share, 'rviz', 'robotbase.rviz')

    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    configured_params = RewrittenYaml(
        source_file=params_file,
        root_key='',
        param_rewrites={
            # RewrittenYaml converts values with Python's literal rules.  Use
            # capitalized booleans here so they cannot be interpreted as the
            # undefined Python names ``true`` / ``false``.
            'use_sim_time': 'True',
            'use_realtime_priority': 'False',
            'enable_stamped_cmd_vel': 'False',
            'base_frame_id': 'sirius3/base_footprint',
            'robot_base_frame': 'sirius3/base_footprint',
            'base_frame': 'sirius3/base_footprint',
            'odom_frame_id': 'sirius3/odom',
            'odom_frame': 'sirius3/odom',
            'odom_topic': '/odom',
            'scan_topic': '/scan',
            'robot_radius': '0.53',
            'cmd_vel_out_topic': 'cmd_vel_safe',
            # These frame keys occur alongside legitimate ``map`` values, so
            # they must be rewritten by their full YAML paths.
            'local_costmap.local_costmap.ros__parameters.global_frame':
                'sirius3/odom',
            'behavior_server.ros__parameters.local_frame': 'sirius3/odom',
            'docking_server.ros__parameters.fixed_frame': 'sirius3/odom',
        },
        convert_types=True,
    )
    parameter_file = ParameterFile(configured_params, allow_substs=True)

    simulator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sim_launch),
        launch_arguments={'gui': gui}.items(),
    )
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_launch),
        launch_arguments={
            'params_file': configured_params,
            'use_sim_time': 'True',
            'use_composition': 'False',
            'autostart': 'True',
        }.items(),
    )
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[parameter_file, {'yaml_filename': map_file, 'use_sim_time': True}],
    )
    map_lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_sim_map',
        output='screen',
        parameters=[{
            'autostart': True,
            'node_names': ['map_server'],
            'use_sim_time': True,
        }],
    )
    perfect_localization = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_sim_odom',
        output='screen',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', '0',
            '--frame-id', 'map', '--child-frame-id', 'sirius3/odom',
        ],
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
        DeclareLaunchArgument('map', default_value=default_map),
        DeclareLaunchArgument('params_file', default_value=default_params),
        simulator,
        TimerAction(
            period=5.0,
            actions=[
                perfect_localization,
                map_server,
                map_lifecycle_manager,
                nav2,
                rviz_node,
            ],
        ),
    ])
