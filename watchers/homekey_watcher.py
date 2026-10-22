#!/usr/bin/env python3
# Passive watcher for the LG RCU "Home" key (raw code 773 on /dev/input/event1
# on this TV - find your own device/code with the capture method in the README).
# Never grabs the device, never blocks normal remote behavior.
# On Home key-down, launches the custom home screen app.

import struct
import subprocess
import time

DEV = "/dev/input/event1"
STRUCT_FMT = "<IIHHi"
STRUCT_SIZE = struct.calcsize(STRUCT_FMT)
HOME_CODE = 773
TARGET_APP = "com.naveen.customhome"


def launch_custom_home():
    # Launching an already-running app just resurfaces the old instance
    # (stale content). Close it first so each Home press loads fresh.
    try:
        subprocess.run(
            ["luna-send", "-n", "1", "-f",
             "luna://com.webos.applicationManager/closeByAppId",
             '{"id":"%s"}' % TARGET_APP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except Exception:
        pass
    try:
        subprocess.Popen(
            ["luna-send", "-n", "1", "-f",
             "luna://com.webos.applicationManager/launch",
             '{"id":"%s"}' % TARGET_APP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main():
    while True:
        try:
            with open(DEV, "rb") as f:
                while True:
                    chunk = f.read(STRUCT_SIZE)
                    if len(chunk) != STRUCT_SIZE:
                        break
                    sec, usec, typ, code, val = struct.unpack(STRUCT_FMT, chunk)
                    if typ == 1 and code == HOME_CODE and val == 1:
                        launch_custom_home()
        except Exception:
            time.sleep(2)


if __name__ == "__main__":
    main()
