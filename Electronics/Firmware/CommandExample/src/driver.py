import os
import time
import logging

import PyCmdMessenger
from find_port import find_port


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(level=logging.DEBUG)
    return logging.getLogger(name)


log = get_logger(__name__)


class RealMicrocontrollerService:
    """
    Microcontroller service for connecting to the Arduino/ESP32
    running CmdMessenger. Supports pumps A, B, and C.
    """

    def __init__(self):
        #log.info("Initializing microcontroller service")
        found, com_port = find_port(os.getenv("DEVICE_ID"))

        if not found:
            log.error("No suitable device found.")
            raise RuntimeError("No suitable device found")

        #log.info("Connected to the device: %s", com_port)
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
            ["kReadColor", "III"]    # 7  R,G,B as three uint16 / ints
        ]

        self._board = board
        self.comm = PyCmdMessenger.CmdMessenger(board, commands)
        log.info("Messenger initialized")

        # Read initial "Arduino has started!" acknowledgement (if present)
        #msg = self.comm.receive()
        #log.info("Initial communication: %s", msg)

    # ------------ internal helper ------------

    def _receive_once(self, context: str):
        """Read one message and log it; handle None safely."""
        msg = self.comm.receive()
        if msg is None:
            log.warning("No response received for %s", context)
            return None
        #log.info("%s response: %s", context, msg)
        return msg

    def _send_start(self, cmd_name: str,
                    state: bool, speed: int, direction: bool,
                    label: str) -> bool:
        """Common helper to start/stop a specific pump."""
        #log.info(
        #    "Setting pump %s: state=%s, speed=%d, dir=%s",
        #    label, state, speed, direction
        #)
        try:
            self.comm.send(cmd_name, state, speed, direction)
        except Exception as e:
            #log.error("Error sending %s: %s", cmd_name, e)
            return False

        msg = self._receive_once(cmd_name)
        if msg is None:
            return False

        if msg[0] != "kAcknowledge":
            #log.warning("Unexpected response to %s: %s", cmd_name, msg)
            pass

        return True

    # ------------ public API ------------

    def stopPumps(self):
        """Stop all pumps."""
        #log.info("Sending stop command to all pumps")
        self.comm.send("kStop")
        msg = self._receive_once("kStop")  # expects kAcknowledge, ["Stopped"]

        if msg is None:
            return "No response"

        return msg[1]

    def set_state(self,
                  stateA: bool = False,
                  speedA: int = 0,
                  dirA: bool = True) -> bool:
        """
        Set state of pump A.

        Args:
            stateA: True to run, False to stop.
            speedA: 0–65535 (unsigned int on Arduino).
            dirA: Direction flag.
        """
        return self._send_start("kStart", stateA, speedA, dirA, "A")

    def set_state_b(self,
                    stateB: bool = False,
                    speedB: int = 0,
                    dirB: bool = True) -> bool:
        """
        Set state of pump B.
        """
        return self._send_start("kStartB", stateB, speedB, dirB, "B")

    def set_state_c(self,
                    stateC: bool = False,
                    speedC: int = 0,
                    dirC: bool = True) -> bool:
        """
        Set state of pump C.
        """
        return self._send_start("kStartC", stateC, speedC, dirC, "C")

    def close(self):
        """
        Close the serial connection (best-effort).
        """
        try:
            if hasattr(self._board, "serial") and self._board.serial:
                self._board.serial.close()
                #log.info("Serial connection closed (serial)")
            elif hasattr(self._board, "_serial") and self._board._serial:
                self._board._serial.close()
                #log.info("Serial connection closed (_serial)")
        except Exception as e:
            log.error("Error closing connection: %s", e)


    def read_color(self):
        """
        Request current color (R, G, B) from the AS7343 sensor.

        Returns:
            (red, green, blue) as ints, or None on error.
        """
        # log.info("Requesting current color from microcontroller")
        try:
            # no arguments; Arduino will respond with kReadColor + 3 ints
            self.comm.send("kReadColor")
        except Exception as e:
            #log.error("Error sending kReadColor: %s", e)
            return None

        msg = self._receive_once("kReadColor")
        if msg is None:
            return None

        # msg = [command_name, [args...], timestamp]
        cmd = msg[0]
        args = msg[1]

        # Arduino might send kError if something went wrong
        if cmd == "kError":
            log.error("Color sensor error from MCU: %s", args[0] if args else "")
            return None

        if cmd != "kReadColor":
            log.warning("Unexpected response to kReadColor: %s", msg)
            return None

        if not isinstance(args, (list, tuple)) or len(args) != 3:
            log.warning("kReadColor returned %d args instead of 3", len(args) if args is not None else -1)
            return None

        red, green, blue = args
        # log.info("Color reading: R=%s G=%s B=%s", red, green, blue)
        return int(red), int(green), int(blue)

    def read_color_name(self):
        """
        Returns a very rough color label ("red", "green", "blue", or "unknown")
        based on which channel is largest.
        """
        rgb = self.read_color()

        if rgb is None:
            return None

        r, g, b = rgb
        max_val = max(r, g, b)

        if max_val == 0:
            return "unknown"

        if max_val == r and r > g * 1.1 and r > b * 1.1:
            return "red"
        if max_val == g and g > r * 1.1 and g > b * 1.1:
            return "green"
        if max_val == b and b > r * 1.1 and b > g * 1.1:
            return "blue"

        return "yellow?"




def main():
    service = RealMicrocontrollerService()

    color = service.read_color()
    print("Raw color (R,G,B):", color)

    label = service.read_color_name()
    print("Dominant color label:", label)

    iR, iG, iB = color

    with open("src/results.txt", "a", encoding="utf-8") as f:
        f.write(f"Background color: {color} {label}\n")



    # Example: start all three pumps
    service.set_state(stateA=True, speedA=4096, dirA=True)
    service.set_state_b(stateB=True, speedB=4096, dirB=True)
    #service.set_state_c(stateC=True, speedC=4000, dirC=True)

    # Run for 50 seconds
    time.sleep(50)
    service.stopPumps()

    print("-----------------------------------------------")
    color = service.read_color()
    nR, nG, nB = color
    print("Raw color (R,G,B):", color)
    #print("-----------------------------------------------")
    label = service.read_color_name()
    print("Dominant color label:", label)
    #print("-----------------------------------------------")
    with open("src/results.txt", "a", encoding="utf-8") as f:
        f.write(f"End color: {color} {label}\n--------------------\n")
    
    time.sleep(10)
    service.set_state_c(stateC=True, speedC=4000, dirC=False)

    time.sleep(70)
    # Stop all pumps
    service.stopPumps()

    print(iR-nR, iG-nG, iB-nB)
    # Optionally close
    service.close()


if __name__ == "__main__":
    main()
