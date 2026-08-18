#!/usr/bin/env python3

import os
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


def generate_launch_description():
    driver_share = get_package_share_directory('velodyne_driver')
    pointcloud_share = get_package_share_directory('velodyne_pointcloud')
    laserscan_share = get_package_share_directory('velodyne_laserscan')

    with open(os.path.join(
            driver_share, 'config', 'VLP16-velodyne_driver_node-params.yaml'),
            encoding='utf-8') as config_file:
        driver_params = yaml.safe_load(config_file)['velodyne_driver_node']['ros__parameters']
    with open(os.path.join(
            pointcloud_share, 'config', 'VLP16-velodyne_transform_node-params.yaml'),
            encoding='utf-8') as config_file:
        pointcloud_params = yaml.safe_load(config_file)['velodyne_transform_node']['ros__parameters']
    with open(os.path.join(
            laserscan_share, 'config', 'default-velodyne_laserscan_node-params.yaml'),
            encoding='utf-8') as config_file:
        laserscan_params = yaml.safe_load(config_file)['velodyne_laserscan_node']['ros__parameters']

    tf_prefix = LaunchConfiguration('tf_prefix')
    driver_params['frame_id'] = PathJoinSubstitution([tf_prefix, 'lidar_link'])
    pointcloud_params['calibration'] = os.path.join(
        pointcloud_share, 'params', 'VLP16db.yaml')

    container = ComposableNodeContainer(
        name='velodyne_container', namespace='', package='rclcpp_components',
        executable='component_container', output='both',
        composable_node_descriptions=[
            ComposableNode(
                package='velodyne_driver', plugin='velodyne_driver::VelodyneDriver',
                name='velodyne_driver_node', parameters=[driver_params]),
            ComposableNode(
                package='velodyne_pointcloud', plugin='velodyne_pointcloud::Transform',
                name='velodyne_transform_node', parameters=[pointcloud_params]),
            ComposableNode(
                package='velodyne_laserscan', plugin='velodyne_laserscan::VelodyneLaserScan',
                name='velodyne_laserscan_node', parameters=[laserscan_params]),
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('tf_prefix', default_value='robot'),
        container,
    ])
