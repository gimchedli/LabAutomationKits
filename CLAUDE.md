# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a lab automation teaching kit that demonstrates hardware-software integration for automated liquid handling and color sensing using ESP32 microcontrollers and peristaltic pumps. The project consists of three main components:

1. **Firmware** (C++/Arduino) - ESP32 microcontroller firmware for controlling pumps and sensors
2. **API** (Python/FastAPI) - REST API for interfacing with hardware over serial communication
3. **BayesianOpt** (Python) - Bayesian optimization examples for automated experimentation

## Hardware Architecture

The system uses **CmdMessenger** protocol for bidirectional serial communication between Python (host) and ESP32 (microcontroller). Commands are defined with matching IDs on both sides:

- **Arduino side**: Enum in `main.cpp` (e.g., `kWatchdog`, `kStart`, `kStop`, `kReadColor`)
- **Python side**: Command list in `driver.py` with matching order and format strings

**Critical**: Command IDs must match in order between Arduino and Python. Format strings use:
- `?` = bool
- `I` = unsigned int
- `L` = unsigned long
- `s` = string

### Hardware Components

- **Board**: Adafruit Metro ESP32-S2
- **Pumps**: Up to 3 peristaltic pumps controlled via DF4 motor driver
  - Pins defined in `df4MotorDriver.h` (PWM: 8,16,10,11; DIR: 9,21,13,12)
- **Sensor**: SparkFun AS7343 18-channel color sensor (I2C)
  - Reads RGB values for color detection

## Development Commands

### Firmware Development

**Build and upload firmware** (PlatformIO):
```bash
cd Electronics/Firmware/CommandExample  # or PumpExample, StepExample, Colorreader
pio run -t upload
```

**Monitor serial output**:
```bash
pio device monitor -b 115200
```

**Important**: When modifying firmware commands, update BOTH:
1. Command enum in `src/main.cpp`
2. Commands list in corresponding Python `driver.py`

### Python API Development

**Run FastAPI server**:
```bash
cd API/SimplePump  # or SimplePumpBackground
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Set device ID** (optional, for multi-device setups):
```bash
export DEVICE_ID="your-device-serial-number"
```

**Port detection**: `find_port.py` auto-detects USB serial ports. On Windows, it defaults to COM14 (modify as needed).

### Bayesian Optimization

**Run optimization example**:
```bash
cd BayesianOpt
pip install -r requirements.txt
python bayesianOpt.py
```

**Resume from checkpoint**:
```python
# In bayesianOpt.py:
main(checkPoint="checkpoint.pkl")
```

**Pause/resume**: Press F12 during optimization run.

## Code Structure & Patterns

### Firmware Pattern (Arduino)

Each firmware example follows this structure:
1. **Command enum** - Defines command IDs matching Python
2. **Callback functions** - `On<Command>()` dispatches to `receive<Command>()`
3. **Receive functions** - Parse arguments, execute hardware control, send acknowledgment
4. **Setup** - Initialize serial, hardware (pumps/sensors), attach callbacks
5. **Loop** - Continuously `feedinSerialData()` to process commands

**Key libraries**:
- `CmdMessenger.h` - Serial command protocol
- `dataModel.h` - Pump state structures (`Pump` class)
- `df4MotorDriver.h` - Pump control functions (`StartPumpA()`, etc.)
- `SparkFun_AS7343.h` - Color sensor interface

### Python API Pattern

FastAPI services expose REST endpoints that translate HTTP requests to serial commands:

**SimplePump**: Synchronous API for single pump operations
**SimplePumpBackground**: Async API with background task execution and `/status` endpoint

Core flow:
1. API receives HTTP request
2. `driver.py` sends CmdMessenger command via `PyCmdMessenger`
3. Arduino executes and sends acknowledgment
4. API returns response to client

**Driver methods**:
- `set_state(stateA, speedA, dirA, stepTime)` - Control pump
- `getState()` / `get_state_pretty()` - Query current state
- `stopPumps()` - Emergency stop all pumps
- `check_for_step_done()` - Poll for operation completion

### Bayesian Optimization Pattern

The optimization module demonstrates using `scikit-optimize` to find optimal parameters:
- **evaluateFitness.py** - Define objective function (replace with actual hardware measurements)
- **customCallbacks.py** - Live plotting callback
- **bayesianOpt.py** - Main optimization loop with checkpoint saving

## Common Workflows

### Adding a New Command

1. Add to firmware enum in `main.cpp`:
   ```cpp
   enum {
       kWatchdog,
       // ...
       kYourNewCommand,  // New command ID
   };
   ```

2. Add callback attachment:
   ```cpp
   cmdMessenger.attach(kYourNewCommand, OnYourNewCommand);
   ```

3. Implement callback and receiver:
   ```cpp
   void OnYourNewCommand() { receiveYourNewCommand(); }
   void receiveYourNewCommand() {
       // Parse args, execute, acknowledge
       cmdMessenger.sendCmd(kAcknowledge, "Done");
   }
   ```

4. Update Python `driver.py` commands list:
   ```python
   commands = [
       # ... existing commands ...
       ["kYourNewCommand", "format_string"],
   ]
   ```

5. Add Python method to `RealMicrocontrollerService` class:
   ```python
   def your_new_command(self):
       self.comm.send("kYourNewCommand", args...)
       msg = self.comm.receive()
       return msg[1]
   ```

### Testing Hardware Connection

Run the driver standalone to verify connectivity:
```bash
cd API/SimplePump
python driver.py
```

This executes the `main()` function which sends a test command and waits for completion.

## Important Notes

- **Serial baud rate**: Always 115200 (defined in both Arduino setup and Python driver)
- **Command synchronization**: CmdMessenger expects acknowledgment; blocking calls with 3s timeout
- **Pump safety**: Always implement emergency stop (`kStop` command)
- **Device ID**: Use environment variable `DEVICE_ID` for multi-device setups
- **Duplicate directories**: Ignore directories with "copy" suffix (e.g., "StepExample copy") - these are working duplicates

## File Locations

- Firmware examples: `Electronics/Firmware/*/src/main.cpp`
- Python drivers: `API/*/driver.py`
- FastAPI servers: `API/*/main.py`
- Motor control: `Electronics/Firmware/*/lib/DF4MotorDriver/`
- Data models: `Electronics/Firmware/*/lib/dataModel/`
- Port detection: `API/*/find_port.py`
