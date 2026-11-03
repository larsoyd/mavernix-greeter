import json
import os
import tempfile
import unittest
from pathlib import Path

from mavernix_greeter import cli


class Config(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_defaults_when_missing(self):
        c = cli.load_config(self.d / "none.toml")
        self.assertEqual(c["users"]["hidden"], [])
        self.assertTrue(c["users"]["show_list"])
        self.assertEqual(c["sessions"]["default"], "mavernix")

    def test_values_override_defaults(self):
        p = self.d / "g.toml"
        p.write_text('[users]\nhidden = ["a"]\nshow_list = false\n[sessions]\ndefault = "wayfire"\n')
        c = cli.load_config(p)
        self.assertEqual((c["users"]["hidden"], c["users"]["show_list"], c["sessions"]["default"]),
                         (["a"], False, "wayfire"))

    def test_wrong_types_fall_back(self):
        p = self.d / "g.toml"
        p.write_text('[users]\nhidden = "a"\nshow_list = 3\n')
        c = cli.load_config(p)
        self.assertEqual((c["users"]["hidden"], c["users"]["show_list"]), ([], True))

    def test_broken_toml_gives_defaults(self):
        p = self.d / "g.toml"
        p.write_text("[users\n")
        self.assertEqual(cli.load_config(p), cli.load_config(self.d / "none"))


class Remember(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.f = self.d / "last.json"

    def test_round_trip(self):
        cli.remember(self.f, "ada", "mavernix")
        self.assertEqual(cli.recall(self.f), {"user": "ada", "session": "mavernix"})
        self.assertEqual(self.f.stat().st_mode & 0o777, 0o600)

    def test_bad_names_refused(self):
        for user, session in (("a/b", "x"), ("a", "../x"), ("", "x"), ("a" * 300, "x"), ("a b", "x")):
            with self.assertRaises(ValueError, msg=(user, session)):
                cli.remember(self.f, user, session)
        self.assertFalse(self.f.exists())

    def test_recall_of_garbage_is_empty(self):
        self.f.write_text("{nope")
        self.assertEqual(cli.recall(self.f), {})
        self.f.write_text(json.dumps({"user": "../x", "session": 3}))
        self.assertEqual(cli.recall(self.f), {})

    def test_no_temp_files_left(self):
        cli.remember(self.f, "a", "b")
        cli.remember(self.f, "c", "d")
        self.assertEqual(sorted(os.listdir(self.d)), ["last.json"])


class Power(unittest.TestCase):
    def test_actions_map_to_logind_methods(self):
        self.assertEqual(cli.power_call("poweroff")[-3:], ["PowerOff", "b", "false"])
        self.assertEqual(cli.power_call("reboot")[-3:], ["Reboot", "b", "false"])
        self.assertEqual(cli.power_call("suspend")[-3:], ["Suspend", "b", "false"])

    def test_unknown_action_refused(self):
        with self.assertRaises(ValueError):
            cli.power_call("halt; rm")

    def test_call_is_non_interactive_system_bus(self):
        c = cli.power_call("reboot")
        self.assertEqual(c[:2], ["busctl", "--system"])
        self.assertIn("org.freedesktop.login1", c)

    def test_caps_parse(self):
        out = {"PowerOff": 's "yes"', "Reboot": 's "challenge"', "Suspend": 's "na"'}
        self.assertEqual(cli.power_caps(lambda m: out[m]), {"poweroff": True, "reboot": True, "suspend": False})

    def test_caps_failed_query_is_false(self):
        def broken(m):
            raise OSError("no bus")
        self.assertEqual(cli.power_caps(broken), {"poweroff": False, "reboot": False, "suspend": False})


if __name__ == "__main__":
    unittest.main()
