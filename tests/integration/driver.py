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
    px = list(img.get_flattened_data()) if hasattr(img, "get_flattened_data") else list(img.getdata())
    return sum(1 for p in px if p > 245), sum(px) / len(px)


def check_layout(run):
    lines = re.findall(r"\[greeter\] layout (.*)", run.text())
    for line in lines:
        fields = dict(kv.split("=", 1) for kv in line.split())
        sw, sh = map(int, fields.pop("screen").split("x"))
        rects = {k: tuple(map(int, v.split(","))) for k, v in fields.items()}
        for k, (x, y, w, h) in rects.items():
            if x < 0 or y < 0 or x + w > sw or y + h > sh:
                raise Fail(f"layout {k}={x},{y},{w},{h} leaves the {sw}x{sh} screen")
        names = sorted(rects)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                ax, ay, aw, ah = rects[a]
                bx, by, bw, bh = rects[b]
                if ax < bx + bw + 6 and bx < ax + aw + 6 and ay < by + bh + 6 and by < ay + ah + 6:
                    raise Fail(f"layout {a}={rects[a]} and {b}={rects[b]} closer than 6 px")
    return len(lines)


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


def white_box(path):
    from PIL import Image
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    xs, ys = [], []
    for y in range(h // 3, h - h // 4):
        row = [x for x in range(w // 4, 3 * w // 4) if min(px[x, y]) > 250]
        if len(row) >= 120:
            xs += row
            ys.append(y)
    if not xs:
        raise Fail("no white field found")
    return min(xs), min(ys), max(xs), max(ys), w, h


def fringe(path, box):
    from PIL import Image
    img = Image.open(path).convert("RGB").crop(box)
    px = list(img.get_flattened_data()) if hasattr(img, "get_flattened_data") else list(img.getdata())
    lit = [(r, g, b) for r, g, b in px if max(r, g, b) > 120]
    return max((abs(r - b) for r, g, b in lit), default=-1), len(lit)


def password_ok(run):
    run.wait(r"phase=prompt")
    settled_layout(run)
    line = re.findall(r"\[greeter\] layout (.*)", run.text())[-1]
    x, y, w, h = map(int, dict(kv.split("=", 1) for kv in line.split())["name"].split(","))
    run.shot("name")
    spread, lit = fringe(OUT / "name.png", (x, y, x + w, y + h))
    print(f"[driver] name_fringe max_rb={spread} lit_px={lit}")
    if lit < 20 or spread > 12:
        raise Fail(f"name text is not grey antialiased max_rb={spread} lit_px={lit}")
    time.sleep(0.7)
    run.shot("prompt")
    x0, y0, x1, y1, w, h = white_box(OUT / "prompt.png")
    cy = h / 2
    print(f"[driver] field_px x={x0}..{x1} y={y0}..{y1} screen={w}x{h} bottom_below_centre={y1 + 1 - cy:.0f}")
    if abs((y1 + 1) - (cy + 132)) > 2 or abs((x1 - x0 + 1) - 164) > 4 or abs((x0 + x1 + 1) / 2 - w / 2) > 2:
        raise Fail(f"field geometry off: x={x0}..{x1} y={y0}..{y1}")
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


def fades_to_black(run):
    run.wait(r"phase=prompt")
    settled_layout(run)
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=leaving")
    time.sleep(0.6)
    if run.qs.poll() is None:
        run.shot("after-fade")
        white, mean = brightness(OUT / "after-fade.png")
        print(f"[driver] after_fade mean={mean:.1f}")
        if mean > 3:
            raise Fail(f"screen not black after the exit fade mean={mean:.1f}")
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
    run.wait(r"message kind=visible")
    time.sleep(0.8)
    run.shot("code")
    run.wf.type("123456")
    run.wf.key("KEY_ENTER")
    launched(run)


def expired(run):
    run.wait(r"phase=prompt")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    run.wait(r"message kind=error")
    time.sleep(0.8)
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
    time.sleep(0.8)
    run.shot("launch-error")
    white, mean = brightness(OUT / "launch-error.png")
    if mean < 20 or white < 1000:
        raise Fail(f"the screen did not come back after a failed launch mean={mean:.1f} white={white}")
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=starting from=error event=retry")
    run.wait(r"phase=prompt from=starting")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    launched(run)


def cancel_during_touch(run):
    run.wait(r"users count=2")
    settled_layout(run)
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=info")
    run.wf.key("KEY_ESC")
    run.wait(r"phase=pick from=info event=cancel")
    run.wf.key("KEY_ENTER")
    run.wait(r"phase=starting from=pick event=select")
    run.wait(r"phase=prompt", 10)
    if "auth result=success" in run.text():
        raise Fail("a late answer was taken for a login")
    run.wf.type("right")
    run.wf.key("KEY_ENTER")
    launched(run)


def pick_second_user(run):
    run.wait(r"users count=2")
    settled_layout(run)
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
    run.wait(r"greetd connection lost", 6)
    run.wait(r"phase=error .*problem=lost")
    run.shot("lost")


def two_outputs(run):
    run.wait(r"phase=prompt")
    settled_layout(run)
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


LAYOUT_CHECKED = {"password_ok", "pick_second_user", "expired", "multi", "two_outputs", "fail_start"}


def settled_layout(run, count=1):
    run.wait(r"(\[greeter\] layout .*){%d}" % count if count > 1 else r"\[greeter\] layout", 4)


SCENARIOS = {
    "password_ok": ("password", password_ok, {}),
    "wrong_then_ok": ("password", wrong_then_ok, {}),
    "u2f": ("u2f", u2f, {}),
    "fades_to_black": ("slow_start", fades_to_black, {}),
    "u2f_then_password_typed_early": ("u2f_then_password", u2f_then_password_typed_early, {}),
    "multi": ("multi", multi, {}),
    "expired": ("expired", expired, {}),
    "fail_start": ("fail_start", fail_start, {}),
    "pick_second_user": ("password", pick_second_user, {"STUB_USERS": "ada,bob"}),
    "cancel_during_touch": ("u2f_then_password", cancel_during_touch, {"STUB_USERS": "ada,bob"}),
    "unavailable": (None, unavailable, {}),
    "greetd_dies": ("password", greetd_dies, {"MAVERNIX_GREETER_WATCHDOG_MS": "3000"}),
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
        layouts = check_layout(run)
        if SCENARIO in LAYOUT_CHECKED and layouts == 0:
            raise Fail("no layout was logged")
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
