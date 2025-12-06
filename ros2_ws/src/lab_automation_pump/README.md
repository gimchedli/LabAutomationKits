# lab_automation_pump

ROS 2 package wrapping a pump microcontroller (or a mock) and exposing:

- Action `pump/step` (PumpStep.action) to request a timed pump operation.
- Topic `pump/state` (PumpState.msg) publishing current pump A state.
- Cancel of the action (or future service) acts as emergency stop.

## Run (simulation)

```bash
colcon build --packages-select lab_automation_pump
source install/setup.bash
ros2 launch lab_automation_pump pump.launch.py simulated:=true
```

Send a goal:

```bash
ros2 action send_goal /pump/step lab_automation_pump_interfaces/action/PumpStep "{state: true, speed: 2000, dir: true, duration_ms: 3000}"
```

Cancel (if running):

```bash
ros2 action cancel /pump/step
```

Echo state:

```bash
ros2 topic echo /pump/state
```

## Python client (CLI)

This package provides a simple action client you can run from the command line. It wraps the `PumpStep` action and prints feedback and the final result.

Run the client:

```bash
ros2 run lab_automation_pump pump_client --state 1 --speed 2000 --dir 1 --duration 3000
```

Arguments (defaults in parentheses):

- `--state` (1): 1 to enable/run, 0 to disable.
- `--speed` (2000): Motor speed (int) as expected by firmware.
- `--dir` (1): 1 forward, 0 reverse.
- `--duration` (3000): Duration in milliseconds.
- `--action` (pump/step): Action name if you use a non-default namespace.

Examples:

```bash
# Run forward at 3000 for 3s (default action name)
ros2 run lab_automation_pump pump_client --state 1 --speed 3000 --dir 1 --duration 3000

# Use a different action name (e.g., namespaced launch)
ros2 run lab_automation_pump pump_client --action my_ns/pump/step --state 1 --speed 2000 --dir 0 --duration 1500
```

Exit codes:

- 0: Goal succeeded
- 1: Goal completed with failure result
- 2: Action server not available (timeout)
- 3: Goal rejected by server

While the goal is running, the client prints feedback with elapsed time and progress percentage. On completion, it prints the action result message.

## Hardware mode

Supply `device_id` (or rely on first detected port) and set `simulated:=false`:

```bash
ros2 launch lab_automation_pump pump.launch.py simulated:=false device_id:=USB-SERIAL
```

### Adjustable parameters

You can tune runtime behavior via ROS 2 parameters when launching:

- `simulated` (bool): Use mock driver instead of hardware (default true in examples).
- `device_id` (string): Hardware device identifier (serial ID) or leave empty for auto.
- `state_publish_rate_hz` (double): Rate of publishing `pump/state` (default 2.0 Hz).
- `feedback_rate_hz` (double): Action feedback frequency (default 40.0 Hz for snappier progress updates). Example:

```bash
ros2 launch lab_automation_pump pump.launch.py simulated:=true feedback_rate_hz:=60.0
```

Higher feedback rates increase console verbosity; adjust to your needs.

## Troubleshooting

- Ensure you have permissions to access the serial device (e.g., add your user to the `dialout` group on Linux).
- Check the serial connection parameters (baud rate, port) match those of the microcontroller firmware.
- If the node logs "No response from device on getState", verify the microcontroller is powered on and connected properly. You may need to reset the microcontroller.