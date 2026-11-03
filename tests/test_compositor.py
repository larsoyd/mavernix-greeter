import configparser
import tempfile
import unittest
from pathlib import Path

from mavenix_greeter import compositor


def ini(text):
    c = configparser.ConfigParser(interpolation=None)
    c.read_string(text)
    return c


class Ini(unittest.TestCase):
    def build(self, theme=None, keyboard=None):
        return ini(compositor.wayfire_ini(theme or {}, keyboard or {}, "/usr/lib/mavenix-greeter/run-greeter"))

    def test_minimal_plugins_and_no_escape_hatches(self):
        c = self.build()
        self.assertEqual(c["core"]["plugins"].split(), ["autostart"])
        self.assertEqual(c["core"]["exit"], "none")
        self.assertEqual(c["core"]["xwayland"], "false")
        self.assertEqual(c["autostart"]["autostart_wf_shell"], "false")
        self.assertEqual(c["workarounds"]["discard_command_output"], "false")
        self.assertEqual(c["autostart"]["greeter"], "/usr/lib/mavenix-greeter/run-greeter")

    def test_outputs_from_theme(self):
        theme = {"display": {"outputs": [
            {"name": "DP-1", "mode": "3440x1440@180000", "position": "0,0", "scale": 1, "transform": "normal"},
            {"name": "HDMI-A-1", "mode": "1920x1080@60", "position": "5000,200", "scale": 0.75}]}}
        c = self.build(theme)
        self.assertEqual(c["output:DP-1"]["mode"], "3440x1440@180000")
        self.assertEqual(c["output:HDMI-A-1"]["scale"], "0.75")
        self.assertEqual(c["output:HDMI-A-1"]["position"], "5000,200")
        self.assertNotIn("transform", c["output:HDMI-A-1"])

    def test_bad_output_values_dropped(self):
        theme = {"display": {"outputs": [
            {"name": "DP-1]\n[core", "mode": "auto"},
            {"name": "DP-2", "mode": "1920x1080\nplugins = x", "position": "a,b", "scale": 99, "transform": "evil"},
            {"name": "DP-3", "mode": "off"}]}}
        c = self.build(theme)
        self.assertEqual(c["core"]["plugins"].split(), ["autostart"])
        self.assertNotIn("output:DP-1]", c.sections())
        self.assertEqual(dict(c["output:DP-2"]), {})
        self.assertEqual(c["output:DP-3"]["mode"], "off")

    def test_cursor_from_theme_checked(self):
        c = self.build({"cursor": {"theme": "SeaLion", "size": 48}})
        self.assertEqual((c["input"]["cursor_theme"], c["input"]["cursor_size"]), ("SeaLion", "48"))
        c = self.build({"cursor": {"theme": "../../x", "size": 100000}})
        self.assertNotIn("cursor_theme", c["input"])
        self.assertEqual(c["input"]["cursor_size"], "24")

    def test_keyboard_values_checked(self):
        c = self.build(keyboard={"layout": "no,us", "variant": ",intl", "options": "grp:alt_shift_toggle", "model": "pc105"})
        self.assertEqual(c["input"]["xkb_layout"], "no,us")
        self.assertEqual(c["input"]["xkb_options"], "grp:alt_shift_toggle")
        c = self.build(keyboard={"layout": "us\n[core]"})
        self.assertNotIn("xkb_layout", c["input"])

    def test_background_colour_is_qt_free_rgba(self):
        c = self.build({"background": {"color2": "#10203040"}})
        self.assertEqual(c["core"]["background_color"], "#10203040")
        c = self.build({"background": {"color2": "nope"}})
        self.assertEqual(c["core"]["background_color"], "#000000ff")


class Keyboard(unittest.TestCase):
    def test_x11_keymap_file(self):
        p = Path(tempfile.mkdtemp()) / "00-keyboard.conf"
        p.write_text('Section "InputClass"\n  Identifier "system-keyboard"\n  Option "XkbLayout" "no"\n'
                     '  Option "XkbModel" "pc105"\n  Option "XkbOptions" "terminate:ctrl_alt_bksp"\nEndSection\n')
        self.assertEqual(compositor.system_keyboard(p), {"layout": "no", "model": "pc105", "options": "terminate:ctrl_alt_bksp"})

    def test_missing_keymap_is_empty(self):
        self.assertEqual(compositor.system_keyboard(Path("/nonexistent")), {})

    def test_theme_keyboard_wins(self):
        self.assertEqual(compositor.pick_keyboard({"keyboard": {"layout": "de"}}, {"layout": "no"})["layout"], "de")
        self.assertEqual(compositor.pick_keyboard({}, {"layout": "no"})["layout"], "no")


class Fonts(unittest.TestCase):
    def test_conf_adds_theme_fonts_and_private_cache(self):
        conf = compositor.fontconfig("/var/lib/t/current/fonts", "/run/user/9/g/fc")
        self.assertIn("<include ignore_missing=\"yes\">/etc/fonts/fonts.conf</include>", conf)
        self.assertIn("<dir>/var/lib/t/current/fonts</dir>", conf)
        self.assertIn("<cachedir>/run/user/9/g/fc</cachedir>", conf)

    def test_markup_in_paths_refused(self):
        with self.assertRaises(ValueError):
            compositor.fontconfig("/x/<evil>", "/c")


class Drm(unittest.TestCase):
    def test_card_by_driver(self):
        root = Path(tempfile.mkdtemp())
        for card, driver in (("card0", "amdgpu"), ("card1", "nvidia")):
            d = root / card / "device"
            d.mkdir(parents=True)
            (root / "drivers" / driver).mkdir(parents=True)
            (d / "driver").symlink_to(root / "drivers" / driver)
        (root / "card1-DP-1").mkdir()
        self.assertEqual(compositor.drm_device("nvidia", root), "/dev/dri/card1")
        self.assertEqual(compositor.drm_device("i915", root), "")
        self.assertEqual(compositor.drm_device("", root), "")
        self.assertEqual(compositor.drm_device("../x", root), "")


if __name__ == "__main__":
    unittest.main()
