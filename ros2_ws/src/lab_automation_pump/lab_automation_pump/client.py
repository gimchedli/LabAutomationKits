import argparse
import sys
from typing import Optional

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from lab_automation_pump_interfaces.action import PumpStep


class PumpClient(Node):
    def __init__(self, action_name: str = 'pump/step'):
        super().__init__('pump_client')
        self._client = ActionClient(self, PumpStep, action_name)

    def send_goal(self, state: bool, speed: int, direction: bool, duration_ms: int) -> int:
        if not self._client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Action server not available')
            return 2

        goal = PumpStep.Goal()
        goal.state = bool(state)
        goal.speed = int(speed)
        goal.dir = bool(direction)
        goal.duration_ms = int(duration_ms)

        self.get_logger().info(f'Sending goal: state={goal.state} speed={goal.speed} dir={goal.dir} duration_ms={goal.duration_ms}')

        send_future = self._client.send_goal_async(goal, feedback_callback=self.feedback_cb)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()

        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected')
            return 3

        self.get_logger().info('Goal accepted')
        get_result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, get_result_future)
        result = get_result_future.result().result
        self.get_logger().info(f'Result: success={result.success} message={result.message}')
        return 0 if result.success else 1

    def feedback_cb(self, feedback_msg: PumpStep.Feedback):
        fb = feedback_msg.feedback
        self.get_logger().info(f'Feedback: elapsed={fb.elapsed_s:.2f}s progress={fb.progress*100:.0f}% {fb.detail}')


def parse_args(argv: Optional[list[str]] = None):
    p = argparse.ArgumentParser(description='Pump action client')
    p.add_argument('--state', type=int, default=1, help='1 to enable, 0 to disable (default 1)')
    p.add_argument('--speed', type=int, default=2000)
    p.add_argument('--dir', type=int, default=1, help='1 forward, 0 reverse (default 1)')
    p.add_argument('--duration', type=int, default=3000, help='Duration in ms (default 3000)')
    p.add_argument('--action', type=str, default='pump/step', help='Action name (default pump/step)')
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None):
    args = parse_args(argv)
    rclpy.init()
    node = PumpClient(action_name=args.action)
    try:
        ret = node.send_goal(bool(args.state), int(args.speed), bool(args.dir), int(args.duration))
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(ret)


if __name__ == '__main__':
    main()
