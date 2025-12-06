import os
import time
import logging
from typing import Optional, Tuple

import PyCmdMessenger
from find_port import find_port

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(level=logging.DEBUG)
    return logging.getLogger(name)


log = get_logger(__name__)


class RealMicrocontrollerService:
    """
    Microcontroller service for connecting to the Arduino/ESP32
    running CmdMessenger. Supports pumps A, B, and C + color read.
    """

    def __init__(self):
        found, com_port = find_port(os.getenv("DEVICE_ID"))

        if not found:
            log.error("No suitable device found.")
            raise RuntimeError("No suitable device found")

        self._current_port_id = 1

        # Create board object
        board = PyCmdMessenger.ArduinoBoard(
            com_port,
            baud_rate=115200,
            timeout=3.0,
        )
        log.debug("Using board: %s", board)

        # Command list MUST match enum order in the Arduino sketch
        commands = [
            ["kWatchdog",    "s"],   # 0
            ["kAcknowledge", "s"],   # 1
            ["kError",       "s"],   # 2
            ["kStart",       "?I?"], # 3  pump A
            ["kStartB",      "?I?"], # 4  pump B
            ["kStartC",      "?I?"], # 5  pump C
            ["kStop",        ""],    # 6  stop all pumps
            ["kReadColor",   "III"]  # 7  R,G,B as three uint16 / ints
        ]

        self._board = board
        self.comm = PyCmdMessenger.CmdMessenger(board, commands)
        log.info("Messenger initialized")

    # ------------ internal helper ------------

    def _receive_once(self, context: str):
        """Read one message and log it; handle None safely."""
        msg = self.comm.receive()
        if msg is None:
            log.warning("No response received for %s", context)
            return None
        return msg

    def _send_start(self, cmd_name: str,
                    state: bool, speed: int, direction: bool,
                    label: str) -> bool:
        """Common helper to start/stop a specific pump."""
        try:
            self.comm.send(cmd_name, state, speed, direction)
        except Exception as e:
            log.error("Error sending %s: %s", cmd_name, e)
            return False

        msg = self._receive_once(cmd_name)
        if msg is None:
            return False

        if msg[0] != "kAcknowledge":
            log.warning("Unexpected response to %s: %s", cmd_name, msg)

        return True

    # ------------ public API: pumps ------------

    def stopPumps(self) -> str:
        """Stop all pumps."""
        self.comm.send("kStop")
        msg = self._receive_once("kStop")  # expects kAcknowledge, ["Stopped"]

        if msg is None:
            return "No response"

        return str(msg[1])

    def set_state(self,
                  stateA: bool = False,
                  speedA: int = 0,
                  dirA: bool = True) -> bool:
        """Pump A."""
        return self._send_start("kStart", stateA, speedA, dirA, "A")

    def set_state_b(self,
                    stateB: bool = False,
                    speedB: int = 0,
                    dirB: bool = True) -> bool:
        """Pump B."""
        return self._send_start("kStartB", stateB, speedB, dirB, "B")

    def set_state_c(self,
                    stateC: bool = False,
                    speedC: int = 0,
                    dirC: bool = True) -> bool:
        """Pump C."""
        return self._send_start("kStartC", stateC, speedC, dirC, "C")

    # ------------ public API: color ------------

    def read_color(self) -> Optional[Tuple[int, int, int]]:
        """
        Request current color (R, G, B) from the AS7343 sensor.

        Returns:
            (red, green, blue) as ints, or None on error.
        """
        try:
            self.comm.send("kReadColor")
        except Exception as e:
            log.error("Error sending kReadColor: %s", e)
            return None

        msg = self._receive_once("kReadColor")
        if msg is None:
            return None

        cmd = msg[0]
        args = msg[1]

        if cmd == "kError":
            log.error("Color sensor error from MCU: %s", args[0] if args else "")
            return None

        if cmd != "kReadColor":
            log.warning("Unexpected response to kReadColor: %s", msg)
            return None

        if not isinstance(args, (list, tuple)) or len(args) != 3:
            log.warning(
                "kReadColor returned %d args instead of 3",
                len(args) if args is not None else -1,
            )
            return None

        red, green, blue = args
        return int(red), int(green), int(blue)

    def read_color_name(self,
                        rgb: Optional[Tuple[int, int, int]] = None,
                        baseline: Optional[Tuple[int, int, int]] = None
                        ) -> Optional[str]:
        """
        Returns a very rough color label ("red", "green", "blue", or "unknown").

        If 'rgb' is None, this function will call read_color().
        If 'baseline' is provided (r0,g0,b0), the classification is based on
        the difference (r-r0, g-g0, b-b0), which helps remove background bias.
        """
        if rgb is None:
            rgb = self.read_color()

        if rgb is None:
            return None

        r, g, b = rgb

        if baseline is not None:
            br, bg, bb = baseline
            r -= br
            g -= bg
            b -= bb

        r = max(r, 0)
        g = max(g, 0)
        b = max(b, 0)

        if r == 0 and g == 0 and b == 0:
            return "unknown"

        if r >= g and r >= b:
            return "red"
        if g >= r and g >= b:
            return "green"
        if b >= r and b >= g:
            return "blue"

        return "unknown"

    # ------------ lifecycle ------------

    def close(self):
        """Close the serial connection (best-effort)."""
        try:
            if hasattr(self._board, "serial") and self._board.serial:
                self._board.serial.close()
                log.info("Serial connection closed (serial)")
            elif hasattr(self._board, "_serial") and self._board._serial:
                self._board._serial.close()
                log.info("Serial connection closed (_serial)")
        except Exception as e:
            log.error("Error closing connection: %s", e)


# ============================================================
#                   F A S T A P I   P A R T
# ============================================================

app = FastAPI(title="Pump + Color API")

service: Optional[RealMicrocontrollerService] = None
baseline_rgb: Optional[Tuple[int, int, int]] = None


class PumpCommand(BaseModel):
    pump: str        # "A" | "B" | "C"
    state: bool      # True = run, False = stop
    speed: int = 0   # 0–65535
    direction: bool = True  # True/False


@app.on_event("startup")
def startup_event():
    global service, baseline_rgb
    log.info("Starting up RealMicrocontrollerService...")
    service = RealMicrocontrollerService()

    # take one baseline reading at startup (optional)
    baseline_rgb = service.read_color()
    log.info("Baseline RGB at startup: %s", baseline_rgb)


@app.on_event("shutdown")
def shutdown_event():
    global service
    log.info("Shutting down, stopping pumps and closing connection...")
    if service is not None:
        try:
            service.stopPumps()
        except Exception:
            pass
        service.close()
    service = None


def _get_service() -> RealMicrocontrollerService:
    if service is None:
        raise HTTPException(status_code=500, detail="Hardware service not initialized")
    return service


@app.get("/color")
def get_color():
    """
    Read raw RGB from sensor.
    """
    svc = _get_service()
    rgb = svc.read_color()
    if rgb is None:
        raise HTTPException(status_code=500, detail="Failed to read color")

    r, g, b = rgb
    return {"r": r, "g": g, "b": b}


@app.get("/color/name")
def get_color_name():
    """
    Read RGB and return a simple color name, using baseline if available.
    """
    svc = _get_service()
    rgb = svc.read_color()
    if rgb is None:
        raise HTTPException(status_code=500, detail="Failed to read color")

    name = svc.read_color_name(rgb=rgb, baseline=baseline_rgb)
    if name is None:
        raise HTTPException(status_code=500, detail="Failed to classify color")

    return {"r": rgb[0], "g": rgb[1], "b": rgb[2], "name": name}


@app.post("/baseline/recalibrate")
def recalibrate_baseline():
    """
    Take a new baseline reading (e.g. with empty cuvette).
    """
    global baseline_rgb
    svc = _get_service()
    rgb = svc.read_color()
    if rgb is None:
        raise HTTPException(status_code=500, detail="Failed to read color")

    baseline_rgb = rgb
    return {"baseline": {"r": rgb[0], "g": rgb[1], "b": rgb[2]}}


@app.post("/pumps")
def control_pump(cmd: PumpCommand):
    """
    Control a single pump A/B/C.
    """
    svc = _get_service()
    pump = cmd.pump.upper()
    ok = False

    if pump == "A":
        ok = svc.set_state(stateA=cmd.state, speedA=cmd.speed, dirA=cmd.direction)
    elif pump == "B":
        ok = svc.set_state_b(stateB=cmd.state, speedB=cmd.speed, dirB=cmd.direction)
    elif pump == "C":
        ok = svc.set_state_c(stateC=cmd.state, speedC=cmd.speed, dirC=cmd.direction)
    else:
        raise HTTPException(status_code=400, detail="pump must be 'A', 'B' or 'C'")

    if not ok:
        raise HTTPException(status_code=500, detail="Failed to send pump command")

    return {"status": "ok", "pump": pump, "state": cmd.state, "speed": cmd.speed, "direction": cmd.direction}


@app.post("/stop")
def stop_all_pumps():
    """
    Stop all pumps.
    """
    svc = _get_service()
    msg = svc.stopPumps()
    return {"status": "ok", "message": msg}


# Optional: run with `python this_file.py`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
