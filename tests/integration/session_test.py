#!/usr/bin/env python3
"""session_test.py OUT_DIR [case...]: runs the real greeter-session script in a private headless setup."""
import json
import os
import pty
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = Path(sys.argv[1])


class Fail(Exception):
    pass


def tree(tmp, greeter=True):
    lib, share, state = tmp / "lib", tmp / "share", tmp / "state"
    for d in (lib, share / "themes", state / "greeter"):
        d.mkdir(parents=True)
    (share / "themes" / "neutral").symlink_to(REPO / "data/themes/neutral")
    if greeter:
        (share / "greeter").symlink_to(REPO / "src/greeter")
    for name in ("greeter-session", "run-greeter"):
        (lib / name).symlink_to(REPO / "src/session" / name)
    (lib / "helper").write_text(f"""#!/usr/bin/env bash
case $1 in users|sessions|power-caps|remember|power) exec python3 {HERE}/stub_helper.py "$@";; esac
PYTHONPATH={REPO}/src/helper exec python3 -c 'import sys; from mavernix_greeter import cli; sys.exit(cli.main(sys.argv[1:]))' "$@"
""")
    (lib / "text-greeter").write_text("#!/usr/bin/env bash\nt=n\n[[ -t 1 ]] && t=y\n"
                                      f"echo fallback tty_out=$t >> {tmp}/fallback.txt\n"
                                      "sleep 0.2\n")
    (tmp / "bin").mkdir()
    (tmp / "bin" / "systemd-cat").write_text(f"#!/usr/bin/env bash\ncat >> {tmp}/journal.txt\n")
    (tmp / "bin" / "systemd-cat").chmod(0o755)
    (tmp / "wayfire-test").write_text("#!/usr/bin/env bash\n"
                                      "sed -i 's/^plugins = autostart$/plugins = autostart ipc stipc/' \"$2\"\n"
                                      "exec wayfire \"$@\"\n")
    for p in (lib / "helper", lib / "text-greeter", tmp / "wayfire-test"):
        p.chmod(0o755)
    return lib, share, state


def ipc(path, method, deadline=15, **data):
    end = time.time() + deadline
    while True:
        try:
            s = socket.socket(socket.AF_UNIX)
            s.settimeout(5)
            s.connect(str(path))
            break
        except OSError:
            if time.time() > end:
                raise Fail("no compositor socket")
            time.sleep(0.05)
    body = json.dumps({"method": method, "data": data}).encode()
    s.sendall(struct.pack("<I", len(body)) + body)
    n = struct.unpack("<I", s.recv(4, socket.MSG_WAITALL))[0]
    return json.loads(s.recv(n, socket.MSG_WAITALL))


def keys(sock, text):
    for k in text:
        for state in (True, False):
            ipc(sock, "stipc/feed_key", key=k, state=state)
        time.sleep(0.03)


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"


class Case:
    def __init__(self, name, tmp, greeter=True, compositor=None, tty=False, theme=False, tries=None, extra=None,
                 stub=None, files=None):
        self.name, self.tmp = name, tmp
        self.out = OUT / name
        self.out.mkdir(parents=True, exist_ok=True)
        lib, share, state = tree(tmp, greeter)
        self.state = state
        if theme:
            (state / "theme").mkdir()
            (state / "theme" / "snap-1").symlink_to(REPO / "data/themes/neutral", target_is_directory=True)
            (state / "theme" / "current").symlink_to("snap-1")
        if tries is not None:
            (state / "greeter" / "tries").write_text(f"{tries}\n")
        if stub:
            compositor = str(tmp / "compositor-stub")
            Path(compositor).write_text(stub.format(tmp=tmp))
            Path(compositor).chmod(0o755)
        for name_, text in (files or {}).items():
            (tmp / name_).write_text(text)
        extra = {k: v.format(tmp=tmp) for k, v in (extra or {}).items()}
        self.rt = tmp / "rt"
        self.rt.mkdir(mode=0o700)
        self.sock = self.rt / "wf.sock"
        self.greetd_sock = self.rt / "greetd.sock"
        self.greetd = subprocess.Popen([sys.executable, REPO / "tests/fake_greetd.py", self.greetd_sock, "password",
                                        self.out / "greetd.log"], env={**os.environ, "FAKE_GREETD_LIMIT": "40"})
        for _ in range(100):
            if self.greetd_sock.exists():
                break
            time.sleep(0.05)
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
        env.update(XDG_RUNTIME_DIR=str(self.rt), GREETD_SOCK=str(self.greetd_sock), _WAYFIRE_SOCKET=str(self.sock),
                   MAVERNIX_GREETER_LIBDIR=str(lib), MAVERNIX_GREETER_DATADIR=str(share),
                   MAVERNIX_GREETER_STATEDIR=str(state), MAVERNIX_GREETER_FALLBACK=str(lib / "text-greeter"),
                   MAVERNIX_GREETER_COMPOSITOR=compositor or str(tmp / "wayfire-test"),
                   STUB_RECORD=str(self.out / "helper.log"), WLR_DRM_DEVICES="none",
                   PATH=f"{tmp / 'bin'}:{os.environ['PATH']}", **(extra or {}))
        if tty:
            master, slave = pty.openpty()
            self.master = master
            self.proc = subprocess.Popen([lib / "greeter-session"], env=env, stdin=slave, stdout=slave, stderr=slave,
                                         start_new_session=True)
            os.close(slave)
            self.journal = tmp / "journal.txt"
        else:
            self.log = open(self.out / "session.log", "w")
            self.proc = subprocess.Popen([lib / "greeter-session"], env=env, stdout=self.log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
            self.journal = self.out / "session.log"

    def text(self):
        return self.journal.read_text(errors="replace") if self.journal.exists() else ""

    def tries(self):
        return (self.state / "greeter" / "tries").read_text().strip()

    def wait_for(self, what, pred, deadline):
        end = time.time() + deadline
        while time.time() < end:
            if pred():
                return
            time.sleep(0.05)
        raise Fail(f"waited for {what} deadline_s={deadline}")

    def compositor_pid(self):
        p = self.rt / "mavernix-greeter" / "compositor.pid"
        self.wait_for("compositor pid", p.exists, 10)
        return int(p.read_text())

    def finish(self, deadline=10):
        try:
            return self.proc.wait(deadline)
        except subprocess.TimeoutExpired:
            raise Fail(f"greeter-session still running after {deadline}s")

    def cleanup(self):
        for p in (self.proc, self.greetd):
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGKILL) if p is self.proc else p.kill()
                except ProcessLookupError:
                    pass
                p.wait(5)

    def fallback_count(self):
        f = self.tmp / "fallback.txt"
        return f.read_text().count("fallback") if f.exists() else 0

    def fallback_text(self):
        f = self.tmp / "fallback.txt"
        return f.read_text() if f.exists() else ""


def case_launch(c):
    wf = c.compositor_pid()
    c.wait_for("prompt", lambda: "phase=prompt" in c.text(), 15)
    keys(c.sock, ["KEY_R", "KEY_I", "KEY_G", "KEY_H", "KEY_T", "KEY_ENTER"])
    c.wait_for("greetd start", lambda: "event=start" in (c.out / "greetd.log").read_text(), 10)
    t0 = time.monotonic()
    rc = c.finish()
    ms = (time.monotonic() - t0) * 1000
    print(f"[session] case=launch start_to_exit_ms={ms:.0f}")
    if rc != 0 or c.fallback_count() or alive(wf):
        raise Fail(f"rc={rc} fallback={c.fallback_count()} compositor_alive={alive(wf)}")
    if ms > 3000:
        raise Fail(f"greeter took {ms:.0f} ms to leave after launch, greetd terminates it at 5000")
    bad = [ln for ln in c.text().splitlines() if "invalid option value" in ln or "Error in file" in ln]
    if bad or "Starting wayfire" not in c.text():
        raise Fail(f"the compositor refused its config: {bad[:2]}")


def case_qs_crashes(c):
    wf = c.compositor_pid()
    rc = c.finish(25)
    if c.fallback_count() != 1 or alive(wf) or rc != 0:
        raise Fail(f"rc={rc} fallback={c.fallback_count()} compositor_alive={alive(wf)}")
    if c.text().count("result=crashed") != 3:
        raise Fail("expected three greeter tries")


def case_compositor_fails(c):
    rc = c.finish(15)
    if c.fallback_count() != 1 or rc != 0:
        raise Fail(f"rc={rc} fallback={c.fallback_count()}")
    if c.text().count("compositor_exit=") != 4 or "reason=greeter_none" not in c.text():
        raise Fail("the compositor was not tried four times before the text login")


def case_compositor_recovers(c):
    c.wait_for("prompt", lambda: "phase=prompt" in c.text(), 25)
    if c.text().count("compositor_exit=") != 2:
        raise Fail("expected two failed starts before the one that worked")
    c.proc.send_signal(signal.SIGTERM)
    c.finish(5)
    if c.fallback_count():
        raise Fail("the text login was started although the compositor came up")


def case_waits_for_console(c):
    c.wait_for("waiting", lambda: "console=waiting vt=7 active=tty3" in c.text(), 5)
    time.sleep(1.5)
    if (c.rt / "mavernix-greeter" / "compositor.pid").exists():
        raise Fail("the compositor was started on a console that is not shown")
    (c.tmp / "active").write_text("tty7\n")
    c.wait_for("prompt", lambda: "phase=prompt" in c.text(), 20)
    c.proc.send_signal(signal.SIGTERM)
    c.finish(5)
    if "compositor_exit=" in c.text().split("phase=prompt")[0]:
        raise Fail("a compositor start was spent while the console was away")


def case_console_wait_ends(c):
    c.wait_for("end of the wait", lambda: "console=still_away vt=7 waited_s=1" in c.text(), 6)
    c.compositor_pid()
    c.proc.send_signal(signal.SIGTERM)
    c.finish(5)


def case_term_while_waiting(c):
    c.wait_for("waiting", lambda: "console=waiting" in c.text(), 5)
    c.proc.send_signal(signal.SIGTERM)
    rc = c.finish(3)
    if rc != 0 or c.fallback_count():
        raise Fail(f"rc={rc} fallback={c.fallback_count()}")


def case_never_shown(c):
    rc = c.finish(30)
    if c.fallback_count() != 1 or c.text().count("result=not_shown") != 4:
        raise Fail(f"rc={rc} fallback={c.fallback_count()} not_shown={c.text().count('result=not_shown')}")


def case_away_is_not_a_failure(c):
    c.wait_for("end of the wait", lambda: "console=still_away" in c.text(), 6)
    c.compositor_pid()
    time.sleep(3)
    if "result=not_shown" in c.text():
        raise Fail("a greeter nobody could see was stopped for not showing")
    c.proc.send_signal(signal.SIGTERM)
    c.finish(5)


def case_old_status_is_forgotten(c):
    c.wait_for("second try stopped for not showing", lambda: "compositor_try=2 result=not_shown" in c.text(), 12)
    c.proc.send_signal(signal.SIGTERM)
    c.finish(5)


def case_neutral_after_failures(c):
    c.finish(15)
    t = c.text()
    at = t.find("theme=neutral reason=compositor_failed")
    if at < 0 or t[:at].count("compositor_exit=") != 2 or t[at:].count("compositor_exit=") != 2:
        raise Fail("the plain look was not used for the second half of the tries")


def case_crashing_greeter_tries_plain_look(c):
    rc = c.finish(45)
    t = c.text()
    if c.fallback_count() != 1 or t.count("result=crashed") != 6 or "theme=neutral reason=greeter_failed" not in t:
        raise Fail(f"rc={rc} fallback={c.fallback_count()} crashed={t.count('result=crashed')}")


def case_term(c):
    wf = c.compositor_pid()
    c.wait_for("prompt", lambda: "phase=prompt" in c.text(), 15)
    c.proc.send_signal(signal.SIGTERM)
    rc = c.finish(5)
    time.sleep(1.5)
    if "result=crashed" in c.text():
        raise Fail("the greeter was restarted after its compositor was gone")
    if c.fallback_count() or alive(wf):
        raise Fail(f"rc={rc} fallback={c.fallback_count()} compositor_alive={alive(wf)}")


def case_kill(c):
    wf = c.compositor_pid()
    c.wait_for("prompt", lambda: "phase=prompt" in c.text(), 15)
    c.proc.send_signal(signal.SIGKILL)
    c.finish(5)
    c.wait_for("compositor gone after its parent was killed", lambda: not alive(wf), 5)


def case_fallback_keeps_terminal(c):
    c.finish(25)
    if "tty_out=y" not in c.fallback_text():
        raise Fail(f"text login lost the terminal: {c.fallback_text()!r}")
    if "result=fallback" not in c.text():
        raise Fail("fallback reason not in the journal")


def case_failed_theme_set_aside(c):
    c.compositor_pid()
    c.wait_for("set aside", lambda: "theme=neutral reason=imported_theme_failed" in c.text(), 10)
    c.wait_for("shown", lambda: "[greeter] shown" in c.text(), 15)
    c.proc.send_signal(signal.SIGTERM)
    c.finish(5)
    if c.tries() != "0":
        raise Fail(f"a shown greeter did not clear the count tries={c.tries()} log={c.text()[-600:]!r}")


def case_theme_used_below_limit(c):
    c.compositor_pid()
    c.wait_for("prompt", lambda: "phase=prompt" in c.text(), 15)
    if "imported_theme_failed" in c.text():
        raise Fail("theme set aside below the limit")
    c.proc.send_signal(signal.SIGTERM)
    c.finish(5)


def case_no_sessions(c):
    rc = c.finish(25)
    if c.fallback_count() != 1 or "reason=greeter_no_sessions" not in c.text():
        raise Fail(f"rc={rc} fallback={c.fallback_count()} log tail={c.text()[-300:]!r}")
    if c.text().count("result=crashed"):
        raise Fail("no sessions was retried as a crash")


CASES = {
    "launch": (case_launch, {}),
    "qs_crashes": (case_qs_crashes, {"greeter": False}),
    "compositor_fails": (case_compositor_fails, {"compositor": "/bin/false"}),
    "compositor_recovers": (case_compositor_recovers, {"stub": """#!/usr/bin/env bash
n=$(cat {tmp}/starts 2>/dev/null || echo 0)
echo $((n + 1)) > {tmp}/starts
(( n < 2 )) && exit 1
exec {tmp}/wayfire-test "$@"
"""}),
    "waits_for_console": (case_waits_for_console, {"files": {"active": "tty3\n"}, "extra": {
        "XDG_VTNR": "7", "MAVERNIX_GREETER_ACTIVE_VT": "{tmp}/active"}}),
    "console_wait_ends": (case_console_wait_ends, {"files": {"active": "tty3\n"}, "extra": {
        "XDG_VTNR": "7", "MAVERNIX_GREETER_ACTIVE_VT": "{tmp}/active", "MAVERNIX_GREETER_CONSOLE_WAIT": "1"}}),
    "term_while_waiting": (case_term_while_waiting, {"files": {"active": "tty3\n"}, "extra": {
        "XDG_VTNR": "7", "MAVERNIX_GREETER_ACTIVE_VT": "{tmp}/active"}}),
    "never_shown": (case_never_shown, {"stub": "#!/usr/bin/env bash\nexec sleep 40\n",
                                       "extra": {"MAVERNIX_GREETER_SHOW_WAIT": "1"}}),
    "away_is_not_a_failure": (case_away_is_not_a_failure, {
        "stub": "#!/usr/bin/env bash\nexec sleep 40\n", "files": {"active": "tty3\n"}, "extra": {
            "XDG_VTNR": "7", "MAVERNIX_GREETER_ACTIVE_VT": "{tmp}/active", "MAVERNIX_GREETER_CONSOLE_WAIT": "1",
            "MAVERNIX_GREETER_SHOW_WAIT": "1"}}),
    "old_status_is_forgotten": (case_old_status_is_forgotten, {"stub": """#!/usr/bin/env bash
n=$(cat {tmp}/starts 2>/dev/null || echo 0)
echo $((n + 1)) > {tmp}/starts
(( n == 0 )) && echo shown > "$MAVERNIX_GREETER_STATUS" && exit 1
exec sleep 40
""", "extra": {"MAVERNIX_GREETER_SHOW_WAIT": "1"}}),
    "neutral_after_failures": (case_neutral_after_failures, {"compositor": "/bin/false", "theme": True}),
    "crashing_greeter_tries_plain_look": (case_crashing_greeter_tries_plain_look, {"greeter": False, "theme": True}),
    "term": (case_term, {}),
    "kill": (case_kill, {}),
    "fallback_keeps_terminal": (case_fallback_keeps_terminal, {"greeter": False, "tty": True}),
    "failed_theme_set_aside": (case_failed_theme_set_aside, {"theme": True, "tries": 3}),
    "theme_used_below_limit": (case_theme_used_below_limit, {"theme": True, "tries": 2}),
    "no_sessions": (case_no_sessions, {"extra": {"STUB_SESSIONS": "none"}}),
}


def main():
    os.environ.update(WLR_BACKENDS="headless", WLR_RENDERER=os.environ.get("WLR_RENDERER", "pixman"),
                      WLR_HEADLESS_OUTPUTS="1", WLR_LIBINPUT_NO_DEVICES="1", PULSE_SERVER="unix:/nonexistent",
                      KDE_DEBUG="1", QT_FORCE_STDERR_LOGGING="1")
    names = sys.argv[2:] or list(CASES)
    failed = 0
    for name in names:
        body, opts = CASES[name]
        tmp = Path(tempfile.mkdtemp(prefix="gs."))
        c = None
        try:
            c = Case(name, tmp, **opts)
            body(c)
            print(f"[session] case={name} result=pass")
        except Exception as e:
            failed += 1
            print(f"[session] case={name} result=fail reason={e}")
            if c:
                print("\n".join(c.text().splitlines()[-15:]))
        finally:
            if c:
                c.cleanup()
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"[session] cases={len(names)} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
