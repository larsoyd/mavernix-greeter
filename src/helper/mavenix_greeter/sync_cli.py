import argparse
import os
import pwd
import re
import stat
import subprocess
import sys
from pathlib import Path

from . import sync

STATE = Path("/var/lib/mavenix-greeter")
USER = re.compile(r"[a-z_][a-z0-9_-]{0,31}")
READER = Path(__file__).with_name("reader.py")


def check_inbox(inbox, user, uid, root_uid=0):
    if not USER.fullmatch(user):
        return "bad user name"
    try:
        top = os.lstat(inbox)
        own = os.lstat(Path(inbox) / user)
    except OSError as e:
        return f"inbox missing {e.__class__.__name__}"
    if top.st_uid != root_uid or top.st_mode & (stat.S_IWGRP | stat.S_IWOTH) or not stat.S_ISDIR(top.st_mode):
        return "inbox root not owned by root or writable by others"
    if not stat.S_ISDIR(own.st_mode):
        return "user inbox is not a directory"
    if own.st_uid != uid:
        return "user inbox owner mismatch"
    return ""


def reader_cmd(uid, gid):
    return ["setpriv", f"--reuid={uid}", f"--regid={gid}", "--clear-groups", "--no-new-privs",
            "--inh-caps=-all", "--", sys.executable, "-I", str(READER)]


def log(text):
    print(f"[greeter-sync] {text}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mavenix-greeter-sync")
    ap.add_argument("action", choices=["import", "enable", "disable", "reset"])
    ap.add_argument("user", nargs="?")
    args = ap.parse_args(argv)
    if os.geteuid() != 0:
        log("refused reason=not_root")
        return 2
    inbox = STATE / "inbox"
    if args.action == "reset":
        sync.reset(STATE / "theme")
        log("result=reset")
        return 0
    if not args.user or not USER.fullmatch(args.user):
        log("refused reason=bad_user")
        return 2
    pw = pwd.getpwnam(args.user)
    if args.action == "enable":
        inbox.mkdir(mode=0o755, parents=True, exist_ok=True)
        own = inbox / args.user
        own.mkdir(mode=0o700, exist_ok=True)
        os.chown(own, pw.pw_uid, pw.pw_gid, follow_symlinks=False)
        subprocess.run(["systemctl", "enable", "--now", f"mavenix-greeter-sync@{args.user}.path"], check=True, timeout=30)
        log(f"result=enabled user={args.user}")
        return 0
    if args.action == "disable":
        subprocess.run(["systemctl", "disable", "--now", f"mavenix-greeter-sync@{args.user}.path"], timeout=30)
        log(f"result=disabled user={args.user}")
        return 0
    problem = check_inbox(inbox, args.user, pw.pw_uid)
    if problem:
        log(f"refused user={args.user} reason={problem!r}")
        return 1
    r = sync.import_snapshot(inbox / args.user / "snapshot", STATE / "theme", reader_cmd(pw.pw_uid, pw.pw_gid))
    if r.problem:
        log(f"refused user={args.user} reason={r.problem!r} skipped={len(r.skipped)}")
        return 1
    if r.installed is None:
        log(f"result=unchanged user={args.user}")
        return 0
    log(f"result=installed user={args.user} dir={r.installed.name} skipped={len(r.skipped)}")
    return 0
