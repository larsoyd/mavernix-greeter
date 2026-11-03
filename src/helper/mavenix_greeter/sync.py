import json
import os
import re
import shutil
import subprocess
import tarfile
import time
from collections import namedtuple
from pathlib import Path

SCHEMA = "mavenix-greeter.theme"
VERSION = 1
TOTAL = 160 * 1024 * 1024
NAME = r"[A-Za-z0-9_][A-Za-z0-9_.+@ -]{0,95}"
RULES = [
    ("theme", re.compile(r"theme\.json"), "json"),
    ("background", re.compile(r"background\.(?:png|jpe?g|webp)"), "image"),
    ("accounts", re.compile(rf"accounts/{NAME}\.(?:png|jpe?g)"), "image"),
    ("fonts", re.compile(rf"fonts/{NAME}\.(?:ttf|otf|ttc|dfont)"), "font"),
    ("index", re.compile(rf"cursors/{NAME}/index\.theme"), "text"),
    ("cursors", re.compile(rf"cursors/{NAME}/cursors/{NAME}"), "xcursor"),
]
LIMITS = {"theme": 1 << 20, "background": 48 << 20, "accounts": 4 << 20, "fonts": 48 << 20,
          "index": 16 << 10, "cursors": 16 << 20}
MAGIC = {
    "image": (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"RIFF"),
    "font": (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf", b"\x00\x00\x01\x00"),
    "xcursor": (b"Xcur",),
}
Result = namedtuple("Result", "problem skipped installed")


def rule_for(name):
    return next(((key, kind) for key, rx, kind in RULES if rx.fullmatch(name)), None)


def content_ok(kind, data):
    if kind in MAGIC:
        ok = data.startswith(MAGIC[kind])
        return ok and (not data.startswith(b"RIFF") or data[8:12] == b"WEBP")
    if kind == "text":
        try:
            return b"\0" not in data and bool(data.decode("utf-8"))
        except UnicodeDecodeError:
            return False
    return True


def read_stream(stream):
    files, links, skipped, total = {}, {}, [], 0
    with tarfile.open(fileobj=stream, mode="r|") as tar:
        for m in tar:
            rule = rule_for(m.name)
            if rule and m.issym() and rule[0] == "cursors":
                links[m.name] = m.linkname
                continue
            if not rule or not m.isreg() or m.size > LIMITS[rule[0]]:
                skipped.append(m.name)
                continue
            total += m.size
            if total > TOTAL:
                raise ValueError(f"total over {TOTAL} bytes")
            data = tar.extractfile(m).read()
            if content_ok(rule[1], data):
                files[m.name] = data
            else:
                skipped.append(m.name)
    return files, links, skipped


def check_theme(files):
    try:
        theme = json.loads(files["theme.json"])
    except (KeyError, ValueError):
        return None, "theme.json missing or unreadable"
    if not isinstance(theme, dict) or theme.get("schema") != SCHEMA:
        return None, "theme.json schema"
    v = theme.get("version")
    if type(v) is not int or not 1 <= v <= VERSION:
        return None, "theme.json version"
    image = theme.get("background", {}).get("image") if isinstance(theme.get("background"), dict) else None
    if image and image not in files:
        return None, f"background {image!r} missing"
    return theme, ""


def write(path, data):
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    with open(path, "xb") as f:
        f.write(data)
    os.chmod(path, 0o644)


def install(dest, theme, files, links):
    dest.mkdir(mode=0o755, parents=True, exist_ok=True)
    new = dest / f"snap-{time.time_ns()}"
    new.mkdir(mode=0o755)
    files = {**files, "theme.json": (json.dumps(theme, indent=1, sort_keys=True) + "\n").encode()}
    for name, data in files.items():
        write(new / name, data)
    for p in new.rglob("*"):
        if p.is_dir():
            os.chmod(p, 0o755)
    os.chmod(new, 0o755)
    for name, target in links.items():
        if f"{name.rsplit('/', 1)[0]}/{target}" in files:
            (new / name).parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            os.symlink(target, new / name)
    tmp = dest / ".current.tmp"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    os.symlink(new.name, tmp)
    os.replace(tmp, dest / "current")
    for old in dest.glob("snap-*"):
        if old != new:
            shutil.rmtree(old)
    return new


def import_snapshot(snapshot, dest, reader):
    proc = subprocess.Popen(reader + [str(snapshot)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        files, links, skipped = read_stream(proc.stdout)
    except (tarfile.TarError, ValueError) as e:
        proc.kill()
        rc = proc.wait(10)
        if rc > 0:
            return Result(f"reader rc={rc}", [], None)
        return Result(f"total {e}" if "total" in str(e) else f"stream {e}", [], None)
    finally:
        proc.stdout.close()
    try:
        rc = proc.wait(60)
    except subprocess.TimeoutExpired:
        proc.kill()
        rc = -1
    if rc != 0:
        return Result(f"reader rc={rc}", skipped, None)
    theme, problem = check_theme(files)
    if problem:
        return Result(problem, skipped, None)
    return Result("", skipped, install(Path(dest), theme, files, links))
