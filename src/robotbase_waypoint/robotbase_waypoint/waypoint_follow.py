"""Follow Sirius-compatible YAML waypoints using Nav2 NavigateToPose."""

import math
import os
from typing import Optional

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from std_msgs.msg import Bool
from tf2_ros import Buffer, TransformException, TransformListener

from .waypoint_io import load_waypoints


def yaw_to_quaternion(yaw: float):
    """Return z and w for a planar yaw quaternion."""
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class WaypointFollower(Node):
    """Send successive Nav2 goals, with early switching at intermediate points."""

    def __init__(self) -> None:
        super().__init__('koko_waypoint_follower')
        default_prefix = os.environ.get('ROBOTBASE_TF_PREFIX', 'robot')
        self.declare_parameter('waypoint_file', '')
        self.declare_parameter('start_index', 1)
        self.declare_parameter('loop', False)
        self.declare_parameter('default_threshold', 1.0)
        self.declare_parameter('precise_threshold', 0.35)
        self.declare_parameter('stop_duration', 5.0)
        self.declare_parameter('stop_on_failure', False)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('base_frame', f'{default_prefix}/base_footprint')
        self.declare_parameter('safety_cmd_vel_topic', '/cmd_vel_direct')

        waypoint_file = str(self.get_parameter('waypoint_file').value)
        if not waypoint_file:
            raise ValueError('waypoint_file parameter is required')
        self.waypoints = load_waypoints(waypoint_file)
        requested_index = int(self.get_parameter('start_index').value)
        if requested_index < 1 or requested_index > len(self.waypoints):
            raise ValueError(
                f'start_index must be between 1 and {len(self.waypoints)}; '
                f'got {requested_index}')

        self.index = requested_index - 1
        self.loop = bool(self.get_parameter('loop').value)
        self.default_threshold = float(self.get_parameter('default_threshold').value)
        self.precise_threshold = float(self.get_parameter('precise_threshold').value)
        self.stop_duration = float(self.get_parameter('stop_duration').value)
        self.stop_on_failure = bool(self.get_parameter('stop_on_failure').value)
        self.map_frame = str(self.get_parameter('map_frame').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        safety_cmd_vel_topic = str(
            self.get_parameter('safety_cmd_vel_topic').value)
        if self.default_threshold <= 0.0 or self.precise_threshold <= 0.0:
            raise ValueError('threshold parameters must be positive')

        self.action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.stop_publisher = self.create_publisher(Bool, '/stop', 10)
        self.safety_cmd_vel_publisher = self.create_publisher(
            Twist, safety_cmd_vel_topic, 10)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.goal_handle = None
        self.goal_result_future = None
        self.goal_serial = 0
        self.transition_in_progress = False
        self.holding_stop = False
        self.waiting_until = None
        self.waiting_finishes_route = False
        self.finished = False
        self.timer = self.create_timer(0.1, self._timer_callback)

        self._publish_stop(False)
        self.get_logger().info(
            f"Loaded {len(self.waypoints)} waypoints from '{waypoint_file}', "
            f'start={requested_index}, loop={self.loop}, frame={self.base_frame}, '
            f'stop_on_failure={self.stop_on_failure}')

    def start(self) -> None:
        """Wait for Nav2 and dispatch the first waypoint."""
        while rclpy.ok() and not self.action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().info('Waiting for /navigate_to_pose action server...')
        if rclpy.ok():
            self._send_current_goal()

    def _publish_stop(self, value: bool) -> None:
        message = Bool()
        message.data = value
        self.stop_publisher.publish(message)

    def _publish_safety_zero(self) -> None:
        """Stop drivers that retain the last velocity when mux output goes quiet."""
        self.safety_cmd_vel_publisher.publish(Twist())

    def _begin_holding_stop(self) -> None:
        """Hold position by commanding zero velocity without engaging hardware emergency stop."""
        self.holding_stop = True
        self._publish_stop(False)
        self._publish_safety_zero()

    def _send_current_goal(self) -> None:
        if self.finished or self.waiting_until is not None:
            return
        waypoint = self.waypoints[self.index]
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = self.map_frame
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = waypoint.x
        goal.pose.pose.position.y = waypoint.y
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = (
            yaw_to_quaternion(waypoint.angle_radians))

        self.goal_serial += 1
        serial = self.goal_serial
        self.get_logger().info(
            f'[WP:{waypoint.number}] {self.index + 1}/{len(self.waypoints)} '
            f'goal=({waypoint.x:.2f}, {waypoint.y:.2f}, '
            f'{waypoint.angle_radians:.2f} rad)')
        future = self.action_client.send_goal_async(goal)
        future.add_done_callback(
            lambda completed, sent_serial=serial: self._goal_response(completed, sent_serial))

    def _goal_response(self, future, serial: int) -> None:
        if serial != self.goal_serial or self.finished:
            return
        try:
            goal_handle = future.result()
        except Exception as error:  # noqa: BLE001 - ROS future can surface transport errors
            self._handle_failure(f'goal request failed: {error}', serial)
            return
        if not goal_handle.accepted:
            self._handle_failure('goal was rejected by Nav2', serial)
            return
        self.goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        self.goal_result_future = result_future
        result_future.add_done_callback(
            lambda completed, sent_serial=serial: self._goal_result(completed, sent_serial))

    def _goal_result(self, future, serial: int) -> None:
        if serial != self.goal_serial or self.finished or self.waiting_until is not None:
            return
        try:
            wrapped_result = future.result()
        except Exception as error:  # noqa: BLE001
            self._handle_failure(f'goal result failed: {error}', serial)
            return
        if wrapped_result.status == GoalStatus.STATUS_SUCCEEDED:
            waypoint = self.waypoints[self.index]
            self.get_logger().info(f'[WP:{waypoint.number}] reached by Nav2')
            self._arrive_at_waypoint(exact_arrival=True)
        elif wrapped_result.status == GoalStatus.STATUS_ABORTED:
            self._handle_failure('Nav2 aborted the waypoint', serial)
        elif wrapped_result.status == GoalStatus.STATUS_CANCELED:
            self._handle_failure('Nav2 canceled the waypoint', serial)
        else:
            self._handle_failure(
                f'Nav2 returned status {wrapped_result.status}', serial)

    def _timer_callback(self) -> None:
        if self.holding_stop:
            self._publish_safety_zero()
        if self.finished:
            return
        if self.transition_in_progress:
            return
        if self.goal_handle is None and self.waiting_until is None:
            return
        if self.waiting_until is not None:
            if self.get_clock().now() >= self.waiting_until:
                self.holding_stop = False
                self.waiting_until = None
                if self.waiting_finishes_route:
                    self._complete_or_loop()
                else:
                    self._advance()
            return

        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame, self.base_frame, rclpy.time.Time())
        except TransformException as error:
            self.get_logger().warning(
                f'TF {self.map_frame} -> {self.base_frame} unavailable: {error}',
                throttle_duration_sec=2.0)
            return

        waypoint = self.waypoints[self.index]
        dx = waypoint.x - transform.transform.translation.x
        dy = waypoint.y - transform.transform.translation.y
        distance = math.hypot(dx, dy)
        self.get_logger().info(
            f'[WP:{waypoint.number}] distance={distance:.2f} m',
            throttle_duration_sec=1.0)

        needs_pause = waypoint.stop or waypoint.wait_time > 0.0
        is_last = self.index == len(self.waypoints) - 1
        if is_last and not needs_pause:
            return
        threshold = self.precise_threshold if needs_pause else (
            waypoint.threshold if waypoint.threshold > 0.0 else self.default_threshold)
        if distance <= threshold:
            self.get_logger().info(
                f'[WP:{waypoint.number}] threshold reached at {distance:.2f} m')
            self._arrive_at_waypoint(exact_arrival=False)

    def _arrive_at_waypoint(self, exact_arrival: bool) -> None:
        waypoint = self.waypoints[self.index]
        is_last = self.index == len(self.waypoints) - 1
        wait_seconds = waypoint.wait_time
        if waypoint.stop and wait_seconds <= 0.0:
            wait_seconds = self.stop_duration

        if not exact_arrival and self.goal_handle is not None:
            self.transition_in_progress = True
            self.goal_serial += 1
            cancel_future = self.goal_handle.cancel_goal_async()
            cancel_future.add_done_callback(
                lambda completed: self._cancel_finished(
                    completed, wait_seconds, is_last))
            return
        self._finish_arrival(wait_seconds, is_last)

    def _cancel_finished(self, future, wait_seconds: float, is_last: bool) -> None:
        wait_for_result = False
        try:
            response = future.result()
            wait_for_result = bool(response.goals_canceling)
            if not wait_for_result:
                self.get_logger().warning(
                    'Nav2 did not report the previous waypoint as canceling')
        except Exception as error:  # noqa: BLE001
            self.get_logger().warning(f'Waypoint cancel request failed: {error}')
        if wait_for_result and self.goal_result_future is not None:
            self.goal_result_future.add_done_callback(
                lambda completed: self._cancel_result_finished(
                    completed, wait_seconds, is_last))
            return
        self._finish_cancel_transition(wait_seconds, is_last)

    def _cancel_result_finished(
            self, future, wait_seconds: float, is_last: bool) -> None:
        try:
            future.result()
        except Exception as error:  # noqa: BLE001
            self.get_logger().warning(f'Canceled goal result failed: {error}')
        self._finish_cancel_transition(wait_seconds, is_last)

    def _finish_cancel_transition(
            self, wait_seconds: float, is_last: bool) -> None:
        self._publish_safety_zero()
        self._finish_arrival(wait_seconds, is_last)

    def _finish_arrival(self, wait_seconds: float, is_last: bool) -> None:
        self.transition_in_progress = False
        self.goal_handle = None
        self.goal_result_future = None
        waypoint = self.waypoints[self.index]
        if wait_seconds > 0.0:
            self._begin_holding_stop()
            self.waiting_until = self.get_clock().now() + Duration(seconds=wait_seconds)
            self.waiting_finishes_route = is_last
            self.get_logger().info(
                f'[WP:{waypoint.number}] waiting for {wait_seconds:.1f} seconds')
        elif is_last:
            self._complete_or_loop()
        else:
            self._advance()

    def _advance(self) -> None:
        self.index += 1
        self.goal_handle = None
        self._send_current_goal()

    def _complete_or_loop(self) -> None:
        if self.loop:
            self.index = 0
            self.goal_handle = None
            self.get_logger().info('Waypoint loop completed; returning to waypoint 1')
            self._send_current_goal()
            return
        self.finished = True
        self._publish_safety_zero()
        self._publish_stop(False)
        self.get_logger().info('All waypoints completed')
        rclpy.shutdown()

    def _handle_failure(self, message: str, serial: int) -> None:
        if serial != self.goal_serial or self.finished:
            return
        waypoint = self.waypoints[self.index]
        self.get_logger().error(f'[WP:{waypoint.number}] {message}')
        if self.stop_on_failure:
            self.finished = True
            self.holding_stop = False
            self._publish_safety_zero()
            self._publish_stop(False)
            self.get_logger().error('Waypoint following stopped because stop_on_failure=true')
            rclpy.shutdown()
        else:
            self.get_logger().warning(
                f'[WP:{waypoint.number}] Skipping failed waypoint and continuing '
                f'to next waypoint (stop_on_failure=false)')
            self.transition_in_progress = False
            self.goal_handle = None
            self.goal_result_future = None
            if self.index == len(self.waypoints) - 1:
                self._complete_or_loop()
            else:
                self._advance()

    def release_stop(self) -> None:
        """Cancel Nav2, command zero velocity, and release the mux stop lock."""
        if self.goal_handle is not None:
            try:
                future = self.goal_handle.cancel_goal_async()
                rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)
            except Exception as error:  # noqa: BLE001
                self.get_logger().warning(f'Cleanup goal cancellation failed: {error}')
        self._publish_safety_zero()
        self._publish_stop(False)


def main(args=None) -> None:
    """Run the waypoint follower."""
    rclpy.init(args=args)
    node: Optional[WaypointFollower] = None
    try:
        node = WaypointFollower()
        node.start()
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as error:  # noqa: BLE001
        if node is not None:
            node.get_logger().fatal(str(error))
        else:
            print(f'waypoint_follow: {error}')
        if rclpy.ok():
            rclpy.shutdown()
        raise
    finally:
        if node is not None:
            if rclpy.ok():
                node.release_stop()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
