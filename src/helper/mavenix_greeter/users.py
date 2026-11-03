import os
import stat
from pathlib import Path

MAX_AVATAR = 4 * 1024 * 1024
NOLOGIN = ("nologin", "false")


def uid_limits(path):
    found = {}
    try:
        for line in Path(path).read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] in ("UID_MIN", "UID_MAX") and parts[1].isdigit():
                found[parts[0]] = int(parts[1])
    except OSError:
        pass
    return found.get("UID_MIN", 1000), found.get("UID_MAX", 60000)


def shells(path):
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return set()
    return {ln.strip() for ln in lines if ln.strip().startswith("/")}


def avatar(icons, name):
    p = Path(icons) / name
    try:
        st = os.lstat(p)
    except OSError:
        return ""
    return str(p) if stat.S_ISREG(st.st_mode) and 0 < st.st_size <= MAX_AVATAR else ""


def listing(entries, limits, login_shells, icons, hidden=()):
    lo, hi = limits
    out = []
    for pw in sorted(entries, key=lambda p: p.pw_uid):
        if not lo <= pw.pw_uid <= hi or pw.pw_name in hidden:
            continue
        if pw.pw_shell not in login_shells or Path(pw.pw_shell).name in NOLOGIN:
            continue
        full = pw.pw_gecos.split(",")[0].strip()
        out.append({"name": pw.pw_name, "full_name": full or pw.pw_name, "uid": pw.pw_uid,
                    "avatar": avatar(icons, pw.pw_name)})
    return out
