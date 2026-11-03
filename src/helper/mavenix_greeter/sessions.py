import os
import shlex
import stat
from pathlib import Path

MAX_ENTRY = 64 * 1024
RESERVED = set("'\\><~|&;$*?#()`")
VALUE_ESCAPES = {"s": " ", "n": "\n", "t": "\t", "r": "\r", "\\": "\\"}
KINDS = (("wayland-sessions", "wayland"), ("xsessions", "x11"))


def split_exec(line):
    words, cur, i, quoted, started = [], [], 0, False, False
    while i < len(line):
        c = line[i]
        if quoted:
            if c == '"':
                quoted = False
            elif c == "\\":
                nxt = line[i + 1:i + 2]
                if nxt not in ('"', "`", "$", "\\"):
                    raise ValueError(f"bad escape at {i}")
                cur.append(nxt)
                i += 1
            else:
                cur.append(c)
        elif c in " \t":
            if started:
                words.append("".join(cur))
                cur, started = [], False
        elif c == '"':
            quoted = started = True
        elif c in RESERVED or c == "\n":
            raise ValueError(f"unquoted {c!r} at {i}")
        else:
            cur.append(c)
            started = True
        i += 1
    if quoted:
        raise ValueError("unbalanced quote")
    if started:
        words.append("".join(cur))
    words = [w for w in (field_codes(w) for w in words) if w is not None]
    if not words:
        raise ValueError("empty command")
    return words


def greetd_cmd(argv):
    # greetd joins cmd with spaces and hands it to sh, so each word is quoted here
    return [shlex.quote(w) for w in argv]


def field_codes(word):
    if len(word) == 2 and word[0] == "%" and word[1] != "%":
        return None
    return word.replace("%%", "%")


def unescape(value):
    out, i = [], 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value) and value[i + 1] in VALUE_ESCAPES:
            out.append(VALUE_ESCAPES[value[i + 1]])
            i += 2
        else:
            out.append(value[i])
            i += 1
    return "".join(out)


def parse_entry(text):
    keys, group = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            group = line[1:-1]
        elif group == "Desktop Entry" and "=" in line:
            k, v = line.split("=", 1)
            keys.setdefault(k.strip(), unescape(v.strip()))
    return keys


def localized(entry, key, locale):
    lang = (locale or "").split(".")[0].split("@")[0]
    for cand in (lang, lang.split("_")[0]):
        if cand and cand != "C" and f"{key}[{cand}]" in entry:
            return entry[f"{key}[{cand}]"]
    return entry.get(key)


def truthy(entry, key):
    return entry.get(key, "").lower() == "true"


def on_path(name, path):
    if "/" in name:
        p = Path(name)
        return p if p.is_absolute() and os.access(p, os.X_OK) else None
    for d in path:
        p = Path(d) / name
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return None


def trusted(path, owner):
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return (stat.S_ISREG(st.st_mode) and st.st_uid == owner
            and not st.st_mode & (stat.S_IWGRP | stat.S_IWOTH) and st.st_size <= MAX_ENTRY)


def read_session(path, kind, path_dirs, x11_wrapper, locale):
    entry = parse_entry(path.read_text(encoding="utf-8", errors="replace"))
    if truthy(entry, "Hidden") or truthy(entry, "NoDisplay") or "Exec" not in entry:
        return None
    try:
        cmd = split_exec(entry["Exec"])
    except ValueError:
        return None
    if "TryExec" in entry and not on_path(entry["TryExec"], path_dirs):
        return None
    if not on_path(cmd[0], path_dirs):
        return None
    if kind == "x11":
        if not x11_wrapper:
            return None
        cmd = list(x11_wrapper) + cmd
    desktops = [d for d in entry.get("DesktopNames", "").split(";") if d]
    env = [f"XDG_SESSION_TYPE={kind}", f"XDG_SESSION_DESKTOP={path.stem}"]
    if desktops:
        env.append("XDG_CURRENT_DESKTOP=" + ":".join(desktops))
    return {"id": path.stem, "name": localized(entry, "Name", locale) or path.stem,
            "comment": localized(entry, "Comment", locale) or "", "type": kind, "argv": cmd, "cmd": greetd_cmd(cmd), "env": env}


def find(data_dirs, path, owner=0, x11_wrapper=None, preferred=None, locale=None):
    found = {}
    for sub, kind in KINDS:
        for base in data_dirs:
            d = Path(base) / sub
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.desktop")):
                if p.stem in found or not trusted(p, owner):
                    continue
                s = read_session(p, kind, path, x11_wrapper, locale)
                if s:
                    found[s["id"]] = s
    return sorted(found.values(), key=lambda s: (s["id"] != preferred, s["name"].casefold()))
