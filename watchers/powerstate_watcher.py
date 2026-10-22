#!/usr/bin/env python3
# Watches webOS's own power-state service and auto-launches the custom home
# screen whenever the TV transitions INTO "Active" from standby/suspend.
# Runs a persistent `luna-send -i` subscription (one long-lived process,
# webOS pushes a new JSON line on every state change) rather than polling.

import json
import subprocess
import time

TARGET_APP = "com.naveen.customhome"
SUB_CMD = [
    "luna-send", "-i", "-n", "0", "-f",
    "luna://com.webos.service.tvpower/power/getPowerState",
    '{"subscribe":true}',
]


def launch_custom_home():
    try:
        subprocess.run(
            ["luna-send", "-n", "1", "-f",
             "luna://com.webos.applicationManager/closeByAppId",
             '{"id":"%s"}' % TARGET_APP],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3,
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
    prev_state = None
    while True:
        try:
            proc = subprocess.Popen(SUB_CMD, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            for line in proc.stdout:
                try:
                    data = json.loads(line.decode(errors="replace"))
                except Exception:
                    continue
                state = data.get("state")
                if not state:
                    continue
                if prev_state is not None and prev_state != "Active" and state == "Active":
                    launch_custom_home()
                prev_state = state
            proc.wait()
        except Exception:
            pass
        time.sleep(3)  # subscription dropped (e.g. reboot) - reconnect


if __name__ == "__main__":
    main()
