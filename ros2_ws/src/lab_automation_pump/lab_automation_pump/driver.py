import os
import time
import logging

try:
    import PyCmdMessenger
except Exception:
    PyCmdMessenger = None

from .find_port import find_port


def get_logger(name):
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)


log = get_logger(__name__)


class RealMicrocontrollerService:
    """Hardware-backed driver using PyCmdMessenger."""

    def __init__(self, device_id: str | None = None, baud_rate: int = 115200, timeout: int = 3):
        if PyCmdMessenger is None:
            raise RuntimeError("PyCmdMessenger is not available. Install it to use the real driver.")

        found, comPort = find_port(device_id or os.getenv("DEVICE_ID"))
        if not found or not comPort:
            raise RuntimeError("No suitable device found")

        self._current_port_id = 1
        self._board = PyCmdMessenger.ArduinoBoard(comPort, baud_rate=baud_rate, timeout=timeout)
        commands = [["kWatchdog", "s"],
                    ["kAcknowledge", "s"],
                    ["kError", "s"],
                    ["kGetState", ""],
                    ["kGetStateResult", "?I?"],
                    ["kGetLastStep", ""],
                    ["kGetLastStepResult", "??L?I?"],
                    ["kStep", "?I?L"],
                    ["kStop", ""],
                    ["kStepDone", ""],]
        self.comm = PyCmdMessenger.CmdMessenger(self._board, commands)
        # Wait for arduino to come up
        _ = self.comm.receive()

    def stopPumps(self):
        self.comm.send("kStop")
        try:
            msg = self.comm.receive()
            return msg[1]
        except EOFError:
            return "No response"

    def getState(self):
        self.comm.send("kGetState")
        msg = self.comm.receive()
        if msg is None:
            log.warning("No response from device on getState")
            return None
        return msg[1]

    def get_state_pretty(self):
        raw_state = self.getState()
        if isinstance(raw_state, list) and len(raw_state) >= 3:
            return {
                "pumpA": {
                    "state": bool(raw_state[0]),
                    "speed": int(raw_state[1]),
                    "dir": bool(raw_state[2]),
                },
            }
        return {"raw": raw_state}

    def getLastStep(self):
        self.comm.send("kGetLastStep")
        msg = self.comm.receive()
        return msg[1]

    def set_state(self, stateA: bool = False, speedA: int = 0, dirA: bool = True, stepTime: int = 50000):
        try:
            self.comm.send("kStep", stateA, speedA, dirA, stepTime)
            _ = self.comm.receive()
            return True
        except Exception:
            return False

    def check_for_step_done(self) -> bool:
        try:
            msg = self.comm.receive()
            if msg is not None and msg[0] == "kStepDone":
                _ = self.getState()
                return True
        except EOFError:
            pass
        return False


class MockMicrocontrollerService:
    """Time-based mock service for lecture and tests."""

    def __init__(self):
        self._state = {"pumpA": {"state": False, "speed": 0, "dir": True}}
        self._deadline = 0.0

    def stopPumps(self):
        self._state["pumpA"].update({"state": False, "speed": 0})
        self._deadline = 0.0
        return "stopped"

    def getState(self):
        a = self._state["pumpA"]
        return [int(a["state"]), int(a["speed"]), int(a["dir"]) ]

    def get_state_pretty(self):
        return self._state

    def getLastStep(self):
        a = self._state["pumpA"]
        return [a["state"], a["speed"], 0, a["dir"], 0]

    def set_state(self, stateA: bool = False, speedA: int = 0, dirA: bool = True, stepTime: int = 50000):
        now = time.time()
        self._state["pumpA"].update({"state": stateA, "speed": speedA, "dir": dirA})
        self._deadline = now + (max(stepTime, 0) / 1000.0)
        return True

    def check_for_step_done(self) -> bool:
        if self._deadline == 0.0:
            return True
        if time.time() >= self._deadline:
            # auto-clear state at end
            self._state["pumpA"].update({"state": False, "speed": 0})
            self._deadline = 0.0
            return True
        return False
