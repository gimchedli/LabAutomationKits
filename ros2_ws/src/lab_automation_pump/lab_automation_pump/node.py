import time
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.qos import QoSProfile

from builtin_interfaces.msg import Time as TimeMsg

from lab_automation_pump_interfaces.action import PumpStep
from lab_automation_pump_interfaces.msg import PumpState

from .driver import RealMicrocontrollerService, MockMicrocontrollerService


class PumpControllerNode(Node):
    def __init__(self):
        super().__init__('pump_controller')
        self.declare_parameter('device_id', '')
        self.declare_parameter('simulated', True)
        self.declare_parameter('state_publish_rate_hz', 2.0)
        self.declare_parameter('feedback_rate_hz', 40.0)

        simulated = self.get_parameter('simulated').get_parameter_value().bool_value
        device_id = self.get_parameter('device_id').get_parameter_value().string_value

        if simulated:
            self.get_logger().info('Using mock microcontroller driver')
            self._driver = MockMicrocontrollerService()
        else:
            dev_str = device_id if device_id else 'auto'
            self.get_logger().info(f'Using real microcontroller driver (device_id={dev_str})')
            self._driver = RealMicrocontrollerService(device_id=device_id or None)

        self._current_goal_handle = None
        qos = QoSProfile(depth=10)
        self._state_pub = self.create_publisher(PumpState, 'pump/state', qos)

        self._action_server = ActionServer(
            self,
            PumpStep,
            'pump/step',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

        state_rate = self.get_parameter('state_publish_rate_hz').get_parameter_value().double_value
        self._state_timer = self.create_timer(1.0 / max(state_rate, 0.1), self.publish_state)

    # ---- Action lifecycle callbacks ----
    def goal_callback(self, goal_request: PumpStep.Goal):
        # Basic validation
        if goal_request.duration_ms <= 0:
            self.get_logger().warn('Rejecting goal with non-positive duration')
            return GoalResponse.REJECT
        if goal_request.speed < 0:
            self.get_logger().warn('Rejecting goal with negative speed')
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('Cancel requested')
        # Stop hardware
        self._driver.stopPumps()
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing PumpStep goal')
        self.get_logger().debug(f'Goal details: state={goal_handle.request.state} speed={goal_handle.request.speed} dir={goal_handle.request.dir} duration_ms={goal_handle.request.duration_ms}')
        self._current_goal_handle = goal_handle
        g = goal_handle.request

        # Send command
        ok = self._driver.set_state(g.state, g.speed, g.dir, g.duration_ms)
        start = time.time()
        end_deadline = start + (g.duration_ms / 1000.0) + 0.2  # fudge factor
        feedback_rate = self.get_parameter('feedback_rate_hz').get_parameter_value().double_value
        period = 1.0 / max(feedback_rate, 0.5)
        loop_sleep = min(period / 4.0, 0.005)
        last_fb = 0.0
        success = ok
        detail = 'started' if ok else 'command_failed'

        while rclpy.ok():
            now = time.time()
            elapsed = now - start
            progress = min(max(elapsed / (g.duration_ms / 1000.0), 0.0), 1.0)
            
            # Publish feedback at desired rate
            if now - last_fb >= period:
                fb = PumpStep.Feedback()
                fb.elapsed_s = float(elapsed)
                fb.progress = float(progress)
                fb.detail = detail
                goal_handle.publish_feedback(fb)
                last_fb = now

            # Check cancel
            if goal_handle.is_cancel_requested:
                self.get_logger().info('Goal canceled by client')
                self._driver.stopPumps()
                goal_handle.canceled()
                return PumpStep.Result(success=False, message='canceled')

            # Check hardware completion
            if self._driver.check_for_step_done():
                detail = 'completed'
                break

            if now >= end_deadline:
                detail = 'timeout'
                success = False
                break

            time.sleep(loop_sleep)

        # Clear running state
        self._driver.stopPumps()  # ensure safe state
        result = PumpStep.Result()
        result.success = success
        result.message = detail
        goal_handle.succeed()
        self._current_goal_handle = None
        return result

    # ---- State publishing ----
    def publish_state(self):
        st_pretty = self._driver.get_state_pretty()
        msg = PumpState()
        pumpA = st_pretty.get('pumpA', {})
        msg.state = bool(pumpA.get('state', False))
        # If pump is off, force reported speed to 0 to avoid stale speed values from hardware
        raw_speed = int(pumpA.get('speed', 0))
        msg.speed = raw_speed if msg.state else 0
        msg.dir = bool(pumpA.get('dir', True))
        # last step retrieval is optional
        try:
            last_step = self._driver.getLastStep()
            msg.last_step = str(last_step)
        except Exception:
            msg.last_step = ''
        now = self.get_clock().now().to_msg()
        msg.stamp = TimeMsg(sec=now.sec, nanosec=now.nanosec)
        self._state_pub.publish(msg)

    def destroy_node(self):  # cleanup
        self._action_server.destroy()
        super().destroy_node()


def main(args: Optional[list[str]] = None):
    rclpy.init(args=args)
    node = PumpControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
