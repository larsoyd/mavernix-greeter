import os
import re
from pathlib import Path

NAME = re.compile(r"[A-Za-z0-9_-]{1,32}")
MODE = re.compile(r"off|auto|highres|highrr|\d{2,5}x\d{2,5}(@\d{1,6}(\.\d{1,3})?)?")
POSITION = re.compile(r"-?\d{1,5},-?\d{1,5}")
TRANSFORMS = {"normal", "90", "180", "270", "flipped", "flipped-90", "flipped-180", "flipped-270"}
CURSOR = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_. -]{0,63}")
XKB = re.compile(r"[A-Za-z0-9_,:()+-]{0,128}")
COLOR = re.compile(r"#[0-9a-fA-F]{8}")
XKB_KEYS = {"layout": "XkbLayout", "model": "XkbModel", "variant": "XkbVariant", "options": "XkbOptions"}


def section(obj, key):
    v = obj.get(key) if isinstance(obj, dict) else None
    return v if isinstance(v, dict) else {}


def output_lines(o):
    lines = []
    if isinstance(o.get("mode"), str) and MODE.fullmatch(o["mode"]):
        lines.append(f"mode = {o['mode']}")
    if isinstance(o.get("position"), str) and POSITION.fullmatch(o["position"]):
        lines.append(f"position = {o['position']}")
    s = o.get("scale")
    if type(s) in (int, float) and 0.25 <= s <= 4:
        lines.append(f"scale = {s:g}")
    if o.get("transform") in TRANSFORMS:
        lines.append(f"transform = {o['transform']}")
    return lines


def wayfire_ini(theme, keyboard, client):
    bg = section(theme, "background").get("color2")
    cursor = section(theme, "cursor")
    size = cursor.get("size")
    out = ["[core]", "plugins = autostart", "xwayland = false", "exit = none", "close_top_view = none",
           f"background_color = {bg if isinstance(bg, str) and COLOR.fullmatch(bg) else '#000000ff'}",
           "", "[workarounds]", "discard_command_output = false",
           "", "[autostart]", "autostart_wf_shell = false", f"greeter = {client}",
           "", "[input]", f"cursor_size = {size if type(size) is int and 8 <= size <= 256 else 24}"]
    if isinstance(cursor.get("theme"), str) and CURSOR.fullmatch(cursor["theme"]):
        out.append(f"cursor_theme = {cursor['theme']}")
    for key in XKB_KEYS:
        v = keyboard.get(key)
        if isinstance(v, str) and v and XKB.fullmatch(v):
            out.append(f"xkb_{key} = {v}")
    outputs = section(theme, "display").get("outputs")
    for o in outputs if isinstance(outputs, list) else []:
        if isinstance(o, dict) and isinstance(o.get("name"), str) and NAME.fullmatch(o["name"]):
            out += ["", f"[output:{o['name']}]"] + output_lines(o)
    return "\n".join(out) + "\n"


def system_keyboard(path):
    try:
        text = Path(path).read_text()
    except OSError:
        return {}
    found = {}
    for key, opt in XKB_KEYS.items():
        m = re.search(rf'Option\s+"{opt}"\s+"([^"]*)"', text)
        if m:
            found[key] = m.group(1)
    return found


def pick_keyboard(theme, system):
    own = section(theme, "keyboard")
    return own if own.get("layout") else system


def drm_device(driver, root="/sys/class/drm"):
    if not driver or not NAME.fullmatch(driver):
        return ""
    for card in sorted(Path(root).glob("card[0-9]*")):
        if Path(os.path.realpath(card / "device" / "driver")).name == driver:
            return f"/dev/dri/{card.name}"
    return ""
