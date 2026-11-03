#!/usr/bin/env python3
"""e2e.py OUT_DIR: inside the test container, real greetd and PAM with the installed greeter."""
import json
import os
import pwd
import signal
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
PW = Path("/test/pw").read_text()
LOG = OUT / "greetd.log"
SESSIONS = Path("/var/tmp/runs/sessions.log")
GREETER_UID = pwd.getpwnam("greeter").pw_uid
SOCK = f"/run/user/{GREETER_UID}/wf.sock"
report = open(OUT / "e2e.log", "w")


class Fail(Exception):
    pass


def say(text):
    print(f"[e2e] {text}", file=report, flush=True)


def log():
    return LOG.read_text(errors="replace")


def wait(what, pred, deadline):
    end = time.time() + deadline
    while time.time() < end:
        if pred():
            return
        time.sleep(0.05)
    raise Fail(f"waited for {what} deadline_s={deadline}")


def ipc(method, **data):
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(5)
    s.connect(SOCK)
    body = json.dumps({"method": method, "data": data}).encode()
    s.sendall(struct.pack("<I", len(body)) + body)
    n = struct.unpack("<I", s.recv(4, socket.MSG_WAITALL))[0]
    reply = json.loads(s.recv(n, socket.MSG_WAITALL))
    s.close()
    return reply


def key(name):
    for state in (True, False):
        ipc("stipc/feed_key", key=name, state=state)
    time.sleep(0.03)


def type_text(text):
    for ch in text:
        key("KEY_" + ch.upper())


def procs(names):
    found = []
    for p in Path("/proc").iterdir():
        if p.name.isdigit():
            try:
                if (p / "comm").read_text().strip() in names:
                    found.append(int(p.name))
            except OSError:
                pass
    return found


def sessions():
    return SESSIONS.read_text().splitlines() if SESSIONS.exists() else []


def greeter_up(n):
    wait(f"greeter start {n}", lambda: log().count("[greeter] start available=true") >= n, 30)
    wait(f"users listed {n}", lambda: log().count("users count=2") >= n, 15)
    time.sleep(0.6)
    wayfires = procs({"wayfire"})
    if len(wayfires) != 1:
        raise Fail(f"compositors running={len(wayfires)} at greeter start {n}")
    ipc("stipc/move_cursor", x=1, y=1)
    qs = procs({"qs", "quickshell"})
    env = Path(f"/proc/{qs[0]}/environ").read_bytes().split(b"\0") if qs else []
    if b"GREETER_ENV_PROBE=from-etc-environment" not in env:
        raise Fail("the greeter did not get /etc/environment through PAM")


def login(n, wrong_first=False):
    key("KEY_ENTER")
    wait("prompt", lambda: log().count("phase=prompt") >= prompts[0] + 1, 15)
    prompts[0] += 1
    if wrong_first:
        type_text("wrongbad")
        key("KEY_ENTER")
        wait("real pam failure", lambda: log().count("auth result=failure") >= 1, 20)
        wait("prompt after failure", lambda: log().count("phase=prompt") >= prompts[0] + 1, 20)
        prompts[0] += 1
    t0 = time.time()
    type_text(PW)
    key("KEY_ENTER")
    wait(f"session {n}", lambda: len(sessions()) >= n, 20)
    line = sessions()[n - 1]
    started = float(line.split()[0])
    say(f"round={n} submit_to_session_ms={(started - t0) * 1000:.0f} session={line.split(' ', 1)[1]}")
    if "user=ada" not in line or "type=wayland" not in line or "desktop=testsession" not in line:
        raise Fail(f"wrong session environment: {line}")


prompts = [0]


def main():
    env = {**os.environ, "LD_PRELOAD": "/usr/local/lib/nomlock.so"}
    greetd = subprocess.Popen(["greetd", "--config", "/etc/greetd/config.toml"], env=env,
                              stdout=open(LOG, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    try:
        greeter_up(1)
        login(1, wrong_first=True)
        greeter_up(2)
        login(2)
        greeter_up(3)
        qs = procs({"qs", "quickshell"})
        if len(qs) != 1:
            raise Fail(f"greeter processes={qs}")
        os.kill(qs[0], signal.SIGKILL)
        wait("greeter restarted after crash", lambda: log().count("[greeter] start available=true") >= 4, 20)
        greeter_up(4)
        login(3)
        greeter_up(5)
        if greetd.poll() is not None:
            raise Fail(f"greetd exited rc={greetd.returncode}")
        if "result=fallback" in log():
            raise Fail("text fallback was used")
        say("result=pass rounds=3 crash_recovered=1")
        return 0
    except Fail as e:
        say(f"result=fail reason={e}")
        for line in log().splitlines()[-30:]:
            say("log " + line)
        return 1
    finally:
        os.killpg(greetd.pid, signal.SIGTERM)
        try:
            greetd.wait(5)
        except subprocess.TimeoutExpired:
            os.killpg(greetd.pid, signal.SIGKILL)


if __name__ == "__main__":
    sys.exit(main())
