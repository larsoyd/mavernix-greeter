import os
import tempfile
import unittest
from pathlib import Path

from mavernix_greeter import sessions


def entry(**keys):
    body = "".join(f"{k.replace('_', '[', 1) + ']' if '_' in k else k}={v}\n" for k, v in keys.items())
    return "[Desktop Entry]\n" + body


class Exec(unittest.TestCase):
    def test_plain_words(self):
        self.assertEqual(sessions.split_exec("wayfire -c x"), ["wayfire", "-c", "x"])

    def test_quoted_argument_keeps_spaces(self):
        self.assertEqual(sessions.split_exec('run "a b" c'), ["run", "a b", "c"])

    def test_escapes_inside_quotes(self):
        self.assertEqual(sessions.split_exec(r'sh "a\"b\$c\\d\`e"'), ["sh", 'a"b$c\\d`e'])

    def test_field_codes_dropped_and_percent_kept(self):
        self.assertEqual(sessions.split_exec("app %U --x=100%% %f"), ["app", "--x=100%"])

    def test_unbalanced_quote_refused(self):
        with self.assertRaises(ValueError):
            sessions.split_exec('app "open')

    def test_reserved_character_outside_quotes_refused(self):
        for bad in ("a;b", "a|b", "a`b`", "a $HOME", "a > x"):
            with self.assertRaises(ValueError, msg=bad):
                sessions.split_exec(bad)

    def test_unknown_escape_inside_quotes_refused(self):
        with self.assertRaises(ValueError):
            sessions.split_exec(r'sh "a\qb"')

    def test_empty_refused(self):
        with self.assertRaises(ValueError):
            sessions.split_exec("   ")


class Parse(unittest.TestCase):
    def test_only_desktop_entry_group(self):
        e = sessions.parse_entry("[Other]\nName=No\n[Desktop Entry]\nName=Yes\nExec=x\n[Desktop Action a]\nName=Nope\n")
        self.assertEqual(e["Name"], "Yes")

    def test_value_escapes(self):
        e = sessions.parse_entry("[Desktop Entry]\nName=a\\sb\\tc\\\\d\n")
        self.assertEqual(e["Name"], "a b\tc\\d")

    def test_localized_name(self):
        e = sessions.parse_entry(entry(Name="Plain", Name_nb="Norsk", Exec="x"))
        self.assertEqual(sessions.localized(e, "Name", "nb_NO.UTF-8"), "Norsk")
        self.assertEqual(sessions.localized(e, "Name", "de_DE.UTF-8"), "Plain")
        self.assertEqual(sessions.localized(e, "Name", "C"), "Plain")


class Quote(unittest.TestCase):
    def test_greetd_joined_command_round_trips_through_sh(self):
        import subprocess
        argv = ["printf", "%s|", "a b", "it's", "$HOME", "`x`", "*", ""]
        joined = "exec " + " ".join(sessions.greetd_cmd(argv))
        out = subprocess.run(["/bin/sh", "-c", joined], capture_output=True, text=True, env={}).stdout
        self.assertEqual(out, "a b|it's|$HOME|`x`|*||")


class Find(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("wayfire", "startplasma-x11"):
            p = self.bin / name
            p.write_text("#!/bin/sh\n")
            p.chmod(0o755)
        self.uid = os.getuid()

    def write(self, kind, name, text, mode=0o644):
        d = self.root / "share" / kind
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{name}.desktop"
        p.write_text(text)
        p.chmod(mode)
        return p

    def find(self, **kw):
        kw.setdefault("x11_wrapper", None)
        return sessions.find([self.root / "share"], path=[self.bin], owner=self.uid, **kw)

    def test_wayland_session_found_with_env(self):
        self.write("wayland-sessions", "wayfire", entry(Name="Wayfire", Exec="wayfire", DesktopNames="Wayfire;wlroots;"))
        (s,) = self.find()
        self.assertEqual(s["id"], "wayfire")
        self.assertEqual(s["type"], "wayland")
        self.assertEqual(s["argv"], ["wayfire"])
        self.assertEqual(s["cmd"], ["wayfire"])
        self.assertIn("XDG_SESSION_TYPE=wayland", s["env"])
        self.assertIn("XDG_CURRENT_DESKTOP=Wayfire:wlroots", s["env"])
        self.assertIn("XDG_SESSION_DESKTOP=wayfire", s["env"])

    def test_hidden_and_missing_tryexec_skipped(self):
        self.write("wayland-sessions", "a", entry(Name="A", Exec="wayfire", Hidden="true"))
        self.write("wayland-sessions", "b", entry(Name="B", Exec="wayfire", TryExec="nothere"))
        self.write("wayland-sessions", "d", entry(Name="D", Exec="wayfire", NoDisplay="true"))
        self.write("wayland-sessions", "c", entry(Name="C", Exec="nothere"))
        self.assertEqual(self.find(), [])

    def test_bad_exec_skipped_not_fatal(self):
        self.write("wayland-sessions", "a", entry(Name="A", Exec="wayfire; rm -rf x"))
        self.write("wayland-sessions", "b", entry(Name="B", Exec="wayfire"))
        self.assertEqual([s["id"] for s in self.find()], ["b"])

    def test_writable_by_others_refused(self):
        p = self.write("wayland-sessions", "a", entry(Name="A", Exec="wayfire"))
        p.chmod(0o666)
        self.assertEqual(self.find(), [])

    def test_wrong_owner_refused(self):
        self.write("wayland-sessions", "a", entry(Name="A", Exec="wayfire"))
        self.assertEqual(sessions.find([self.root / "share"], path=[self.bin], owner=self.uid + 1, x11_wrapper=None), [])

    def test_symlink_refused(self):
        real = self.write("wayland-sessions", "real", entry(Name="R", Exec="wayfire"))
        (real.parent / "link.desktop").symlink_to(real)
        self.assertEqual([s["id"] for s in self.find()], ["real"])

    def test_directory_named_like_entry_skipped(self):
        (self.root / "share" / "wayland-sessions" / "x.desktop").mkdir(parents=True)
        self.write("wayland-sessions", "b", entry(Name="B", Exec="wayfire"))
        self.assertEqual([s["id"] for s in self.find()], ["b"])

    def test_unreadable_entry_skipped(self):
        self.write("wayland-sessions", "a", entry(Name="A", Exec="wayfire"), mode=0o000)
        self.write("wayland-sessions", "b", entry(Name="B", Exec="wayfire"))
        self.assertEqual([s["id"] for s in self.find()], ["b"])

    def test_bad_encoding_does_not_crash(self):
        p = self.write("wayland-sessions", "a", "")
        p.write_bytes(b"[Desktop Entry]\nName=\xff\xfe\nExec=wayfire\n")
        self.assertEqual([s["id"] for s in self.find()], ["a"])

    def test_file_owner_checked_on_its_own(self):
        p = self.write("wayland-sessions", "a", entry(Name="A", Exec="wayfire"))
        self.assertIsNotNone(sessions.read_trusted(p, self.uid))
        self.assertIsNone(sessions.read_trusted(p, self.uid + 1))

    def test_fifo_with_a_writer_refused(self):
        d = self.root / "share" / "wayland-sessions"
        d.mkdir(parents=True)
        fifo = d / "f.desktop"
        os.mkfifo(fifo, 0o644)
        fd = os.open(fifo, os.O_RDWR)
        try:
            os.write(fd, entry(Name="F", Exec="wayfire").encode())
            self.assertIsNone(sessions.read_trusted(fifo, self.uid))
        finally:
            os.close(fd)

    def test_writable_folder_refused(self):
        self.write("wayland-sessions", "a", entry(Name="A", Exec="wayfire"))
        (self.root / "share" / "wayland-sessions").chmod(0o777)
        self.assertEqual(self.find(), [])

    def test_oversized_refused(self):
        self.write("wayland-sessions", "a", entry(Name="A", Exec="wayfire") + "#" * 70000)
        self.assertEqual(self.find(), [])

    def test_first_dir_wins_and_wayland_beats_x11(self):
        self.write("wayland-sessions", "plasma", entry(Name="Plasma W", Exec="wayfire"))
        self.write("xsessions", "plasma", entry(Name="Plasma X", Exec="startplasma-x11"))
        (s,) = self.find(x11_wrapper=["/w"])
        self.assertEqual(s["name"], "Plasma W")

    def test_x11_wrapped_or_left_out(self):
        self.write("xsessions", "px", entry(Name="Plasma X", Exec="startplasma-x11"))
        self.assertEqual(self.find(), [])
        (s,) = self.find(x11_wrapper=["/usr/lib/mavernix-greeter/x11-session"])
        self.assertEqual(s["argv"], ["/usr/lib/mavernix-greeter/x11-session", "startplasma-x11"])
        self.assertIn("XDG_SESSION_TYPE=x11", s["env"])

    def test_sorted_by_name_with_preferred_first(self):
        for n in ("zeta", "alpha", "mavernix"):
            self.write("wayland-sessions", n, entry(Name=n.title(), Exec="wayfire"))
        ids = [s["id"] for s in self.find(preferred="mavernix")]
        self.assertEqual(ids, ["mavernix", "alpha", "zeta"])

    def test_missing_dirs_give_empty_list(self):
        self.assertEqual(sessions.find([self.root / "nope"], path=[self.bin], owner=self.uid, x11_wrapper=None), [])


if __name__ == "__main__":
    unittest.main()
