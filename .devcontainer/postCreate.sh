#!/usr/bin/env bash
set -euo pipefail

# Source ROS 2 environment for all shells
echo "source \"/opt/ros/humble/setup.bash\"" >> /home/ubuntu/.bashrc


# Create symbolic link to ros2_ws if exists or create it
if [ ! -d /workspaces/LabAutomationKits/ros2_ws ]; then
  mkdir -p /workspaces/LabAutomationKits/ros2_ws/src
fi

# Ensure vscode user can access serial devices
usermod -aG dialout,video ubuntu 2>/dev/null || true
sudo chmod 666 /dev/ttyACM0

chown -R ubuntu:ubuntu /workspaces/LabAutomationKits

# Pre-build interfaces and node packages if present
if [ -d /workspaces/LabAutomationKits/ros2_ws/src/lab_automation_pump_interfaces ]; then
  cd /workspaces/LabAutomationKits/
  sudo apt update
  sudo apt install python3.10-venv -y
  pip3 install --no-cache-dir -r ros2_ws/src/lab_automation_pump_interfaces/requirements.txt

  cd /workspaces/LabAutomationKits/ros2_ws
  source /opt/ros/humble/setup.sh
  rosdep install -i --from-path src --rosdistro humble -y
  colcon build --packages-select lab_automation_pump_interfaces lab_automation_pump --symlink-install || true
fi

echo "Dev container setup complete."