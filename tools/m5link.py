"""Minimal raw-REPL link for UIFlow2 boards that block mpremote.

Opens the port once (board resets), interrupts the startup app,
enters raw REPL, then execs commands / uploads files in that session.

Usage:
  python m5link.py exec  "print(1+1)"
  python m5link.py cat   /flash/boot.py
  python m5link.py put   localfile.py /flash/file.py [more pairs...]
  python m5link.py reset
"""
import sys
import time

import serial

def _find_port():
    """Find the M5Paper v1.1 by its CH9102 USB-serial bridge
    (VID 0x1A86). Matching loosely is dangerous: the user has other
    ESP32 boards that also enumerate as serial ports, and writing our
    firmware files to one of those would be bad."""
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        if p.vid == 0x1A86:                     # QinHeng CH9102
            return p.device
    found = ", ".join("%s (%s)" % (p.device, p.description)
                      for p in serial.tools.list_ports.comports()) \
        or "none"
    raise RuntimeError(
        "M5Paper (CH9102, VID 1A86) not found. Ports present: %s"
        % found)


PORT = _find_port()


class Link:
    def __init__(self):
        # Open with DTR/RTS deasserted: opening with them asserted
        # holds the ESP32 in reset (or drops it into the bootloader),
        # and the board answers nothing at all.
        self.s = serial.Serial()
        self.s.port = PORT
        self.s.baudrate = 115200
        self.s.timeout = 0.2
        self.s.dtr = False
        self.s.rts = False
        self.s.open()
        # Opening resets the board. Storm interrupts from the very
        # start so we break in during boot, before main.py can reach
        # any code that might wedge the panel.
        self._interrupt()
        self.s.timeout = 2
        self._enter_raw()
        # The interrupted boot leaves half-initialized app modules in
        # sys.modules; purge them so exec always tests fresh code.
        self.exec(
            "import sys\n"
            "for _m in ('main','config','artwork','ui_renderer',"
            "'weather_service','wonder_engine','scoring_engine',"
            "'recommendation_engine','scheduler','wifi_secrets'):\n"
            "    sys.modules.pop(_m, None)\n", quiet=True)

    def _interrupt(self):
        # The board may be powered off (timerSleep) — pulse RTS to
        # wake it, then storm Ctrl-C densely: boot-time I2C retries
        # and M5.begin() can swallow sparse interrupts.
        self.s.timeout = 0.05
        self.s.dtr = False
        self.s.rts = True
        time.sleep(0.3)
        self.s.rts = False
        end = time.time() + 60
        buf = b""
        while time.time() < end:
            self.s.write(b"\x03\x03")
            time.sleep(0.05)
            buf += self.s.read(self.s.in_waiting or 0)
            if b"KeyboardInterrupt" in buf or buf.rstrip().endswith(b">>>"):
                break
        self.s.reset_input_buffer()

    def _enter_raw(self):
        out = b""
        for _ in range(6):
            self.s.write(b"\x03")
            time.sleep(0.2)
            self.s.reset_input_buffer()
            self.s.write(b"\r\x01")     # ctrl-A
            time.sleep(0.6)
            out = self.s.read(self.s.in_waiting or 1)
            if b"raw REPL" in out:
                return
        raise RuntimeError("no raw REPL: %r" % out[-120:])

    def exec(self, code, quiet=False):
        self.s.write(code.encode() + b"\x04")
        # response: "OK" ... \x04 stdout \x04 stderr ... ">"
        deadline = time.time() + 300
        buf = b""
        while time.time() < deadline:
            buf += self.s.read(self.s.in_waiting or 1)
            if buf.endswith(b"\x04>") and buf.count(b"\x04") >= 2:
                break
        if not (buf.endswith(b"\x04>") and buf.count(b"\x04") >= 2):
            raise RuntimeError("exec TIMED OUT; partial output: %r"
                               % buf[:800])
        if not buf.startswith(b"OK"):
            raise RuntimeError("exec failed: %r" % buf[:200])
        body = buf[2:-1]
        stdout, _, stderr = body.partition(b"\x04")
        stderr = stderr.rstrip(b"\x04")
        if stderr:
            raise RuntimeError("device error: %s" % stderr.decode())
        if not quiet and stdout:
            print(stdout.decode(), end="")
        return stdout

    def put(self, local, remote):
        with open(local, "rb") as f:
            data = f.read()
        self.exec("f=open(%r,'wb')" % remote, quiet=True)
        for i in range(0, len(data), 256):
            chunk = data[i:i + 256]
            self.exec("f.write(%r)" % chunk, quiet=True)
        self.exec("f.close()", quiet=True)
        # verify size
        out = self.exec("import os; print(os.stat(%r)[6])" % remote,
                        quiet=True)
        ok = int(out.strip()) == len(data)
        print("%s -> %s  %d bytes  %s"
              % (local, remote, len(data), "OK" if ok else "SIZE MISMATCH"))
        if not ok:
            raise RuntimeError("upload size mismatch for %s" % remote)

    def reset(self):
        self.s.write(b"\x02")    # friendly REPL
        time.sleep(0.2)
        self.s.write(b"\x04")    # soft reset -> runs boot.py + main.py
        time.sleep(0.2)
        self.s.close()


def main():
    cmd = sys.argv[1]
    link = Link()
    if cmd == "exec":
        link.exec(sys.argv[2])
    elif cmd == "cat":
        link.exec("print(open(%r).read())" % sys.argv[2])
    elif cmd == "put":
        pairs = sys.argv[2:]
        for i in range(0, len(pairs), 2):
            link.put(pairs[i], pairs[i + 1])
    elif cmd == "reset":
        link.reset()
        print("reset sent")
        return
    link.s.close()


if __name__ == "__main__":
    main()
