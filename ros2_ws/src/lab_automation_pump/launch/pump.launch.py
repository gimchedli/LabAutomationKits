from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument


def generate_launch_description():
    device_id_arg = DeclareLaunchArgument('device_id', default_value='')
    simulated_arg = DeclareLaunchArgument('simulated', default_value='true')
    state_rate_arg = DeclareLaunchArgument('state_publish_rate_hz', default_value='2.0')
    feedback_rate_arg = DeclareLaunchArgument('feedback_rate_hz', default_value='40.0')

    pump_node = Node(
        package='lab_automation_pump',
        executable='pump_node',
        name='pump_controller',
        parameters=[{
            'device_id': LaunchConfiguration('device_id'),
            'simulated': LaunchConfiguration('simulated'),
            'state_publish_rate_hz': LaunchConfiguration('state_publish_rate_hz'),
            'feedback_rate_hz': LaunchConfiguration('feedback_rate_hz'),
        }],
        respawn=False,
        respawn_delay=5.0,
    )

    return LaunchDescription([
        device_id_arg,
        simulated_arg,
        state_rate_arg,
        feedback_rate_arg,  # must be declared before node uses LaunchConfiguration
        pump_node,
    ])
