#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('robotbase_sim')
    world = os.path.join(pkg_share, 'worlds', 'test_arena.sdf')
    model = os.path.join(pkg_share, 'models', 'robotbase.sdf')
    urdf = os.path.join(pkg_share, 'urdf', 'robotbase.urdf')
    mux_config = os.path.join(pkg_share, 'config', 'twist_mux.yaml')

    with open(urdf, 'r', encoding='utf-8') as urdf_file:
        robot_description = urdf_file.read()

    gui = LaunchConfiguration('gui')

    gazebo_gui = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world],
        output='screen',
        condition=IfCondition(gui),
    )
    gazebo_headless = ExecuteProcess(
        cmd=['gz', 'sim', '-s', '-r', world],
        output='screen',
        condition=UnlessCondition(gui),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_description': robot_description,
            'frame_prefix': 'sirius3/',
        }],
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-file', model,
            '-name', 'sirius3',
            '-x', '0.0', '-y', '0.0', '-z', '0.01', '-Y', '0.0',
        ],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='robotbase_gz_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/model/sirius3/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/model/sirius3/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
            '/velodyne_points/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
        ],
        remappings=[
            ('/model/sirius3/odom', '/odom'),
            ('/model/sirius3/tf', '/tf'),
            ('/velodyne_points/points', '/velodyne_points'),
        ],
    )

    vlp16_to_scan = Node(
        package='velodyne_laserscan',
        executable='velodyne_laserscan_node',
        name='vlp16_to_scan',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'ring': 8,
            'resolution': 0.008726646,
            'use_multi_rings': False,
        }],
        remappings=[
            ('velodyne_points', '/velodyne_points'),
            ('scan', '/scan'),
        ],
    )

    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        name='twist_mux',
        output='screen',
        parameters=[mux_config],
        remappings=[('cmd_vel_out', '/cmd_vel')],
    )

    idle_twist = Node(
        package='robotbase_sim',
        executable='idle_twist_publisher.py',
        name='idle_twist_publisher',
        output='screen',
        parameters=[{'use_sim_time': True, 'publish_rate': 10.0}],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='Start the Gazebo GUI. Set false for a headless run.'),
        gazebo_gui,
        gazebo_headless,
        robot_state_publisher,
        TimerAction(period=1.5, actions=[spawn_robot]),
        TimerAction(period=2.0, actions=[bridge, vlp16_to_scan, twist_mux, idle_twist]),
    ])
