import argparse
import json
import os
import pwd
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from . import compositor, sessions, users

CONFIG = "/etc/mavenix-greeter/greeter.toml"
STATE = "/var/lib/mavenix-greeter/greeter/last.json"
ICONS = "/var/lib/AccountsService/icons"
DATA_DIRS = ["/usr/local/share", "/usr/share"]
PATH = ["/usr/local/bin", "/usr/bin"]
X11_WRAPPER = "/usr/lib/mavenix-greeter/x11-session"
KEYMAP = "/etc/X11/xorg.conf.d/00-keyboard.conf"
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.@-]{0,63}")
POWER = {"poweroff": "PowerOff", "reboot": "Reboot", "suspend": "Suspend"}
DEFAULTS = {"users": {"hidden": [], "show_list": True}, "sessions": {"default": "mavernix"}}


def load_config(path):
    try:
        raw = tomllib.loads(Path(path).read_text())
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        raw = {}
    conf = {}
    for section, keys in DEFAULTS.items():
        given = raw.get(section) if isinstance(raw.get(section), dict) else {}
        conf[section] = {k: given[k] if type(given.get(k)) is type(v) else v for k, v in keys.items()}
    return conf


def valid(name):
    return isinstance(name, str) and NAME.fullmatch(name) is not None


def remember(path, user, session):
    if not (valid(user) and valid(session)):
        raise ValueError("bad user or session name")
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".last.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"user": user, "session": session}, f)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def recall(path):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or not (valid(data.get("user")) and valid(data.get("session"))):
        return {}
    return {"user": data["user"], "session": data["session"]}


def power_call(action):
    if action not in POWER:
        raise ValueError(f"unknown power action {action!r}")
    return ["busctl", "--system", "call", "org.freedesktop.login1", "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager", POWER[action], "b", "false"]


def busctl_can(method):
    out = subprocess.run(["busctl", "--system", "call", "org.freedesktop.login1", "/org/freedesktop/login1",
                          "org.freedesktop.login1.Manager", "Can" + method],
                         capture_output=True, text=True, timeout=5, check=True)
    return out.stdout


def power_caps(query=busctl_can):
    caps = {}
    for action, method in POWER.items():
        try:
            answer = query(method).strip()
        except (OSError, subprocess.SubprocessError):
            answer = ""
        caps[action] = answer in ('s "yes"', 's "challenge"')
    return caps


def read_theme(theme_dir):
    try:
        data = json.loads((Path(theme_dir) / "theme.json").read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def x11_wrapper():
    if all(Path(p).exists() for p in (X11_WRAPPER, "/usr/bin/Xorg", "/usr/bin/xinit")):
        return [X11_WRAPPER]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mavenix-greeter-helper")
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--state", default=STATE)
    ap.add_argument("--data-dir", action="append")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("users")
    sub.add_parser("sessions")
    sub.add_parser("power-caps")
    r = sub.add_parser("remember")
    r.add_argument("user")
    r.add_argument("session")
    p = sub.add_parser("power")
    p.add_argument("action", choices=sorted(POWER))
    c = sub.add_parser("compositor")
    c.add_argument("--theme-dir", required=True)
    c.add_argument("--client", required=True)
    d = sub.add_parser("drm-device")
    d.add_argument("--theme-dir", required=True)
    sub.add_parser("default-session")
    f = sub.add_parser("fontconfig")
    f.add_argument("--theme-dir", required=True)
    f.add_argument("--cache", required=True)
    args = ap.parse_args(argv)
    conf = load_config(args.config)
    if args.cmd == "users":
        found = users.listing(pwd.getpwall(), users.uid_limits("/etc/login.defs"), users.shells("/etc/shells"),
                              ICONS, hidden=tuple(conf["users"]["hidden"]))
        out = {"show_list": conf["users"]["show_list"], "users": found, "last": recall(args.state)}
    elif args.cmd == "sessions":
        found = sessions.find(args.data_dir or DATA_DIRS, PATH, owner=0, x11_wrapper=x11_wrapper(),
                              preferred=conf["sessions"]["default"], locale=os.environ.get("LANG"))
        out = {"sessions": found}
    elif args.cmd == "compositor":
        theme = read_theme(args.theme_dir)
        keyboard = compositor.pick_keyboard(theme, compositor.system_keyboard(KEYMAP))
        sys.stdout.write(compositor.wayfire_ini(theme, keyboard, args.client))
        return 0
    elif args.cmd == "drm-device":
        driver = compositor.section(read_theme(args.theme_dir), "display").get("drm_driver")
        print(compositor.drm_device(driver if isinstance(driver, str) else ""))
        return 0
    elif args.cmd == "fontconfig":
        fonts = Path(args.theme_dir) / "fonts"
        if not fonts.is_dir():
            return 1
        sys.stdout.write(compositor.fontconfig(str(fonts), args.cache))
        return 0
    elif args.cmd == "default-session":
        found = sessions.find(args.data_dir or DATA_DIRS, PATH, owner=0, x11_wrapper=None,
                              preferred=conf["sessions"]["default"])
        if not found:
            return 1
        print(" ".join(found[0]["cmd"]))
        return 0
    elif args.cmd == "power-caps":
        out = power_caps()
    elif args.cmd == "remember":
        remember(args.state, args.user, args.session)
        out = {"ok": True}
    else:
        r = subprocess.run(power_call(args.action), capture_output=True, text=True, timeout=15)
        if r.returncode:
            print(f"[helper] power action={args.action} result=refused rc={r.returncode}", file=sys.stderr)
            return 1
        out = {"ok": True}
    json.dump(out, sys.stdout)
    print()
    return 0
