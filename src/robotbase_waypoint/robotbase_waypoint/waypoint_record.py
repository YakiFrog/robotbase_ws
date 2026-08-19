"""Record the robot map pose into a Sirius-compatible waypoint YAML file."""

import math
import os
from typing import Optional

import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformException, TransformListener

from .waypoint_io import append_waypoint


def quaternion_to_yaw(rotation) -> float:
    """Convert a geometry quaternion to planar yaw."""
    return math.atan2(
        2.0 * (rotation.w * rotation.z + rotation.x * rotation.y),
        1.0 - 2.0 * (rotation.y * rotation.y + rotation.z * rotation.z),
    )


class WaypointRecorder(Node):
    """Record once, or repeatedly after a configured travel distance."""

    def __init__(self) -> None:
        super().__init__('koko_waypoint_recorder')
        default_prefix = os.environ.get('ROBOTBASE_TF_PREFIX', 'robot')
        self.declare_parameter('output_file', '')
        self.declare_parameter('continuous', False)
        self.declare_parameter('distance_threshold', 2.0)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('base_frame', f'{default_prefix}/base_footprint')

        self.output_file = str(self.get_parameter('output_file').value)
        self.continuous = bool(self.get_parameter('continuous').value)
        self.distance_threshold = float(self.get_parameter('distance_threshold').value)
        self.map_frame = str(self.get_parameter('map_frame').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        if not self.output_file:
            raise ValueError('output_file parameter is required')
        if self.distance_threshold <= 0.0:
            raise ValueError('distance_threshold must be positive')

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.last_position = None
        self.timer = self.create_timer(0.2, self._timer_callback)
        mode = 'continuous' if self.continuous else 'one-shot'
        self.get_logger().info(
            f'Recording mode={mode}, output={self.output_file}, '
            f'TF={self.map_frame}->{self.base_frame}')

    def _timer_callback(self) -> None:
        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame, self.base_frame, rclpy.time.Time())
        except TransformException as error:
            self.get_logger().warning(
                f'TF unavailable: {error}', throttle_duration_sec=2.0)
            return

        translation = transform.transform.translation
        if self.continuous and self.last_position is not None:
            distance = math.hypot(
                translation.x - self.last_position[0],
                translation.y - self.last_position[1])
            if distance < self.distance_threshold:
                return

        yaw = quaternion_to_yaw(transform.transform.rotation)
        waypoint = append_waypoint(
            self.output_file, translation.x, translation.y, yaw)
        self.last_position = (translation.x, translation.y)
        self.get_logger().info(
            f'[WP:{waypoint.number}] saved '
            f'({waypoint.x:.3f}, {waypoint.y:.3f}, {waypoint.angle_radians:.3f} rad)')
        if not self.continuous:
            rclpy.shutdown()


def main(args=None) -> None:
    """Run the waypoint recorder."""
    rclpy.init(args=args)
    node: Optional[WaypointRecorder] = None
    try:
        node = WaypointRecorder()
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as error:  # noqa: BLE001
        if node is not None:
            node.get_logger().fatal(str(error))
        else:
            print(f'waypoint_record: {error}')
        if rclpy.ok():
            rclpy.shutdown()
        raise
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
