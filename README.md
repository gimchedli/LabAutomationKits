# LabAutomationKits
Documentation and code for the lab automation teaching kit.

## ROS 2 Setup Options
Choose one of three approaches to get ROS 2 Humble running with this kit. They differ in required host OS and complexity. All examples assume ROS 2 Humble.

| Option | Difficulty | Host OS Flexibility | Recommended For |
|--------|------------|---------------------|-----------------|
| Virtual Machine | Easy | Works on Windows/macOS/Linux | Beginners wanting an isolated, disposable environment |
| Docker Dev Container | More Difficult | Works on Windows/macOS/Linux (with Docker + VS Code) | Developers comfortable with containers & VS Code integration |
| Native Install | Easiest (if Ubuntu 22.04) | Officially supported only on Ubuntu 22.04 (others experimental) | Users already on Ubuntu 22.04 wanting best performance |

### 1. Virtual Machine (Easy)
Use a pre-built Ubuntu 22.04 image with ROS 2 Humble preinstalled.

- [Download VirtualBox Image for Windows/x64](https://ituniversity-my.sharepoint.com/:u:/g/personal/lori_itu_dk/EcF0vUMTxbdDsePFHIzLyaQBFIM2wmdSelUN1CjlTwNcgQ?e=AfF4t7)
- [Download UTM Image for macOS](https://ituniversity-my.sharepoint.com/:u:/g/personal/lori_itu_dk/Edo3XV5jDyJEsEg8z1Ogs1oBLbTdUExYpvdzNP86nPqPfw?e=bXONyh)

Steps:
1. Install VirtualBox (Windows) or UTM (macOS).
2. Import the provided image (OVF for VirtualBox / UTM bundle for macOS).
3. Start the VM and log in (provide credentials if custom; else usually `ubuntu`/`ubuntu`).
4. Verify ROS 2 (see Verification section below).

Useful references:
- VirtualBox: https://www.virtualbox.org/
- UTM: https://mac.getutm.app/
- ROS 2 Docs (Humble): https://docs.ros.org/en/humble/

### 2. Docker Dev Container (More Difficult)
This repository includes a VS Code Dev Container using image `tiryoh/ros2-desktop-vnc:humble` that provides GUI access via VNC.

Quick start:
1. Install Docker (Desktop on Windows/macOS, Engine on Linux).
2. Install VS Code + Dev Containers extension.
3. Open the repo in VS Code and choose: "Dev Containers: Reopen in Container".
4. Access GUI: open `http://localhost:6080` (password: `vncpassword`).

Container user: `ubuntu` / password `ubuntu`. Workspace path: `/workspaces/LabAutomationKits`. After verifying ROS 2 with turtlesim, proceed to the pump example section below to build and run the project. Hardware note: Map the serial device in `.devcontainer/devcontainer.json` via `runArgs` (e.g. `--device=/dev/ttyUSB0`) when using real hardware.

### 3. Native Install (Easiest if Ubuntu 22.04)
If you are already running Ubuntu 22.04 (Jammy), installing ROS 2 Humble natively is straightforward and gives best performance & direct hardware access.

Summary (see official docs for details):
```bash
sudo apt update && sudo apt install -y curl gnupg lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install -y ros-humble-desktop python3-colcon-common-extensions
```

Add sourcing to your shell (optional):
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

After installation and turtlesim verification, build and run the pump (see Pump Example section).

Other OSs: You can attempt native installs on macOS or Windows via experimental approaches (e.g., macOS homebrew or Windows Subsystem for Linux). These paths are less documented—proceed at your own risk.

Official native install docs:
- Ubuntu: https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html
- General Overview: https://docs.ros.org/en/humble/

## Verifying Your ROS 2 Installation (turtlesim)
Run a simple ROS 2 demo to confirm everything works.

Terminal 1 (start turtlesim node):
```bash
# Dev Container or workspace build
source /workspaces/LabAutomationKits/ros2_ws/install/setup.bash
# Native
# source /opt/ros/humble/setup.bash
ros2 run turtlesim turtlesim_node
```

Terminal 2 (list nodes and echo topic):
```bash
# Source again in a new terminal
source /workspaces/LabAutomationKits/ros2_ws/install/setup.bash  # or /opt/ros/humble/setup.bash
ros2 node list
ros2 topic echo /turtle1/pose
```

Optional: control the turtle.
```bash
ros2 run turtlesim turtle_teleop_key
```

If you see pose messages updating and can move the turtle, your installation is working. If not, ensure you sourced the correct setup file.

## Using the Pump Example (After Verification)
Once turtlesim works, follow these steps to build and run the pump example.

1. Build the workspace (only needed once after changes):
```bash
cd /workspaces/LabAutomationKits/ros2_ws
colcon build --packages-select lab_automation_pump_interfaces lab_automation_pump
```

2. Source the workspace (Dev Container):
```bash
source /workspaces/LabAutomationKits/ros2_ws/install/setup.bash
```
	Or (Native Ubuntu install):
```bash
source /workspaces/LabAutomationKits/ros2_ws/install/setup.bash  # after building
# If you added ROS to bashrc you already have /opt/ros/humble sourced.
```

3. Launch simulated pump:
```bash
ros2 launch lab_automation_pump pump.launch.py simulated:=true
```

4. In a new terminal (source again) send a demo action goal:
```bash
source /workspaces/LabAutomationKits/ros2_ws/install/setup.bash
ros2 run lab_automation_pump pump_client --duration 3000 --speed 2000 --state 1 --dir 1
```

Hardware runs: add your serial device mapping in the dev container (`--device=/dev/ttyUSB0`) or ensure correct permissions natively (e.g. add user to `dialout`).
