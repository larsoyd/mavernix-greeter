#!/usr/bin/env python3
import json
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

RT, OUT, HERE, REPO = (Path(os.environ[k]) for k in ("RT", "OUT", "HERE", "REPO"))
SCENARIO = os.environ["SCENARIO"]
SECRETS = ("right", "bad", "next", "123456", "hunter")


class Fail(Exception):
    pass


class Wayfire:
    def __init__(self, path, deadline=15):
        end = time.time() + deadline
        while True:
            try:
                self.s = socket.socket(socket.AF_UNIX)
                self.s.settimeout(5)
                self.s.connect(path)
                return
            except OSError:
                if time.time() > end:
                    raise Fail(f"no compositor socket {path}")
                time.sleep(0.05)

    def call(self, method, **data):
        body = json.dumps({"method": method, "data": data}).encode()
        self.s.sendall(struct.pack("<I", len(body)) + body)
        n = struct.unpack("<I", self.read(4))[0]
        return json.loads(self.read(n))

    def read(self, n):
        b = b""
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c:
                raise Fail("compositor closed its socket")
            b += c
        return b

    def key(self, name):
        self.call("stipc/feed_key", key=name, state=True)
        self.call("stipc/feed_key", key=name, state=False)
        time.sleep(0.03)

    def type(self, text):
        for ch in text:
            self.key("KEY_" + ch.upper())


class Run:
    def __init__(self):
        self.wf = Wayfire(os.environ["_WAYFIRE_SOCKET"])
        self.display = self.wf.call("stipc/get_display")["wayland"]
        self.wf.call("stipc/move_cursor", x=1, y=1)
        self.greetd = None
        self.qs = None
        self.log_path = OUT / "greeter.log"

    def start_greetd(self, scenario):
        sock = RT / "greetd.sock"
        self.greetd = subprocess.Popen([sys.executable, HERE.parent / "fake_greetd.py", sock, scenario, OUT / "greetd.log"],
                                       env={**os.environ, "FAKE_GREETD_LIMIT": "50"})
        for _ in range(100):
            if sock.exists():
                return str(sock)
            time.sleep(0.05)
        raise Fail("fake greetd did not listen")

    def start_greeter(self, greetd_sock, **env):
        e = {**os.environ, "WAYLAND_DISPLAY": self.display, **env}
        if greetd_sock:
            e["GREETD_SOCK"] = greetd_sock
        else:
            e.pop("GREETD_SOCK", None)
        self.qs_log = open(self.log_path, "w")
        self.qs = subprocess.Popen(["qs", "-p", str(REPO / "src/greeter")], env=e,
                                   stdout=self.qs_log, stderr=subprocess.STDOUT)

    def text(self):
        return self.log_path.read_text(errors="replace")

    def wait(self, pattern, deadline=10, source=None):
        end = time.time() + deadline
        while time.time() < end:
            body = source() if source else self.text()
            if re.search(pattern, body):
                return
            if self.qs and self.qs.poll() is not None and not source:
                break
            time.sleep(0.05)
        raise Fail(f"waited for {pattern!r} deadline_s={deadline} greeter_alive={self.qs.poll() is None}")

    def greetd_log(self):
        return (OUT / "greetd.log").read_text()

    def shot(self, name, output=None):
        args = ["grim"] + (["-o", output] if output else []) + [str(OUT / f"{name}.png")]
        subprocess.run(args, env={**os.environ, "WAYLAND_DISPLAY": self.display}, timeout=10, check=True)

    def exited(self, deadline=8):
        try:
            return self.qs.wait(deadline)
        except subprocess.TimeoutExpired:
            raise Fail(f"greeter still running {deadline}s after launch")

    def stop(self):
        for p in (self.qs, self.greetd):
            if p and p.poll() is None:
                p.send_signal(signal.SIGTERM)
                try:
                    p.wait(3)
                except subprocess.TimeoutExpired:
                    p.kill()


def brightness(path):
    from PIL import Image
    img = Image.open(path).convert("L")
    px = list(img.getdata())
    return sum(1 for p in px if p > 245), sum(px) / len(px)


def no_secrets(run):
    for f in OUT.iterdir():
        if f.suffix in (".log", ".txt"):
            body = f.read_text(errors="replace")
            for s in SECRETS:
                if re.search(rf"\b{s}\b", body):
                    raise Fail(f"secret {s!r} found in {f.name}")


def launched(run, session_cmd="'/usr/bin/start desk'"):
    run.wait(r"event=start user=\w+ cmd=", 8, run.greetd_log)
    if session_cmd not in run.greetd_log():
        raise Fail(f"start without the chosen session cmd: {run.greetd_log()}")
    rc = run.exited()
    if rc != 0:
        raise Fail(f"greeter exit={rc}")


def password_ok(run):
    run.wait(r"phase=prompt")
    run.shot("prompt")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=leaving")
    launched(run)
    if "[stub-helper] remember ada mavernix" not in (OUT / "helper.log").read_text():
        raise Fail("choice was not remembered")


def wrong_then_ok(run):
    run.wait(r"phase=prompt")
    run.wf.type("bad")
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=failed")
    run.shot("failed")
    run.wait(r"phase=starting from=failed event=shaken", 5)
    run.wait(r"phase=prompt from=starting")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    launched(run)
    if run.greetd_log().count("event=create user=ada") != 2:
        raise Fail("retry did not create exactly one new session")


def u2f(run):
    run.wait(r"phase=info")
    launched(run)


def u2f_then_password_typed_early(run):
    run.wait(r"phase=info")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    if "phase=prompt" in run.text():
        raise Fail("prompt arrived before typing, the queue was not exercised")
    run.wait(r"phase=verifying from=prompt event=submit", 5)
    launched(run)


def multi(run):
    run.wait(r"phase=prompt")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    run.wait(r"message required=true echo=true")
    run.shot("code")
    run.wf.type("123456")
    run.wf.key("KEY_ENTER")
    launched(run)


def expired(run):
    run.wait(r"phase=prompt")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    run.wait(r"message required=false echo=true error=true")
    for _ in range(2):
        time.sleep(0.3)
        run.wf.type("next")
        run.wf.key("KEY_ENTER")
    launched(run)


def fail_start(run):
    run.wait(r"phase=prompt")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=error from=launching event=error problem=launch")
    run.shot("launch-error")
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=starting from=error event=retry")
    run.wait(r"phase=prompt from=starting")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    launched(run)


def pick_second_user(run):
    run.wait(r"users count=2")
    time.sleep(0.5)
    run.shot("list")
    run.wf.key("KEY_RIGHT")
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=prompt")
    if "event=create user=bob" not in run.greetd_log():
        raise Fail("second user was not chosen")
    run.wf.key("KEY_ESC")
    run.wait(r"phase=pick from=prompt event=cancel")
    run.wait("event=cancel", 3, run.greetd_log)


def unavailable(run):
    run.wait(r"start available=false")
    run.wait(r"users count=")
    time.sleep(0.5)
    run.shot("unavailable")
    if "phase=" in run.text():
        raise Fail("greeter left the unavailable phase")


def greetd_dies(run):
    run.wait(r"phase=prompt")
    run.greetd.kill()
    run.greetd.wait(3)
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    run.wait(r"watchdog phase=verifying", 6)
    run.wait(r"phase=error .*problem=lost")
    run.shot("lost")


def two_outputs(run):
    run.wait(r"phase=prompt")
    time.sleep(0.5)
    outs = run.wf.call("window-rules/list-outputs")
    names = [o["name"] for o in outs] if isinstance(outs, list) else []
    if not names:
        raise Fail(f"list-outputs gave {str(outs)[:200]}")
    for n in names:
        run.shot("output-" + n, n)
    if len(names) != 2:
        raise Fail(f"outputs={names}")
    left = min(outs, key=lambda o: o["geometry"]["x"])["name"]
    for n in names:
        white, mean = brightness(OUT / f"output-{n}.png")
        print(f"[driver] output={n} main={n == left} white_px={white} mean={mean:.1f}")
        if n == left and white < 2000:
            raise Fail(f"main output {n} shows no login field white_px={white}")
        if n != left and (white > 0 or mean < 10):
            raise Fail(f"other output {n} white_px={white} mean={mean:.1f}")


SCENARIOS = {
    "password_ok": ("password", password_ok, {}),
    "wrong_then_ok": ("password", wrong_then_ok, {}),
    "u2f": ("u2f", u2f, {}),
    "u2f_then_password_typed_early": ("u2f_then_password", u2f_then_password_typed_early, {}),
    "multi": ("multi", multi, {}),
    "expired": ("expired", expired, {}),
    "fail_start": ("fail_start", fail_start, {}),
    "pick_second_user": ("password", pick_second_user, {"STUB_USERS": "ada,bob"}),
    "unavailable": (None, unavailable, {}),
    "greetd_dies": ("password", greetd_dies, {"MAVENIX_GREETER_WATCHDOG_MS": "3000"}),
    "two_outputs": ("password", two_outputs, {}),
}


def main():
    fake, body, env = SCENARIOS[SCENARIO]
    run = Run()
    t0 = time.monotonic()
    try:
        sock = run.start_greetd(fake) if fake else None
        run.start_greeter(sock, **env)
        body(run)
        no_secrets(run)
        print(f"[driver] scenario={SCENARIO} result=pass seconds={time.monotonic() - t0:.2f}")
        return 0
    except Exception as e:
        print(f"[driver] scenario={SCENARIO} result=fail reason={e}")
        print("[driver] greeter log tail:\n" + "\n".join(run.text().splitlines()[-25:]))
        return 1
    finally:
        run.stop()


if __name__ == "__main__":
    sys.exit(main())
