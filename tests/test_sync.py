import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from mavernix_greeter import sync

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\0" * 32
XCUR = b"Xcur" + b"\0" * 32
TTF = b"\x00\x01\x00\x00" + b"\0" * 32
THEME = {"schema": "mavernix-greeter.theme", "version": 1, "id": "sea-lion", "background": {"image": "background.jpg"}}


def snapshot(root, files=None, links=None):
    snap = root / "snapshot"
    snap.mkdir(parents=True)
    files = {"theme.json": json.dumps(THEME).encode(), "background.jpg": JPG, **(files or {})}
    for name, data in files.items():
        p = snap / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for name, target in (links or {}).items():
        (snap / name).symlink_to(target)
    return snap


class Import(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.inbox = self.root / "inbox"
        self.dest = self.root / "theme"
        self.reader = [sys.executable, "-I", str(Path(sync.__file__).with_name("reader.py"))]

    def run_import(self):
        return sync.import_snapshot(self.inbox / "snapshot", self.dest, reader=self.reader)

    def installed(self):
        return self.dest / "current"

    def test_valid_snapshot_installed_atomically(self):
        snapshot(self.inbox, {"accounts/ada.png": PNG, "fonts/Face.ttf": TTF, "cursors/Snow/cursors/left_ptr": XCUR,
                              "cursors/Snow/index.theme": b"[Icon Theme]\nName=Snow\n"})
        r = self.run_import()
        self.assertEqual(r.problem, "", r)
        cur = self.installed()
        self.assertTrue(cur.is_symlink())
        self.assertEqual(json.loads((cur / "theme.json").read_text())["id"], "sea-lion")
        self.assertEqual((cur / "accounts/ada.png").read_bytes(), PNG)
        self.assertEqual((cur / "fonts/Face.ttf").stat().st_mode & 0o777, 0o644)
        self.assertEqual(cur.resolve().stat().st_mode & 0o777, 0o755)

    def test_modes_do_not_depend_on_umask(self):
        snapshot(self.inbox, {"fonts/Face.ttf": TTF})
        old = os.umask(0o077)
        try:
            self.run_import()
        finally:
            os.umask(old)
        cur = self.installed().resolve()
        self.assertEqual(cur.stat().st_mode & 0o777, 0o755)
        self.assertEqual((cur / "fonts").stat().st_mode & 0o777, 0o755)
        self.assertEqual((cur / "fonts/Face.ttf").stat().st_mode & 0o777, 0o644)
        self.assertEqual((cur / "theme.json").stat().st_mode & 0o777, 0o644)

    def test_riff_that_is_not_webp_refused(self):
        theme = {**THEME, "background": {"image": "background.webp"}}
        snapshot(self.inbox, {"theme.json": json.dumps(theme).encode(),
                              "background.webp": b"RIFF\0\0\0\0WAVEfmt "})
        self.assertIn("background", self.run_import().problem)
        (self.inbox / "snapshot/background.webp").write_bytes(b"RIFF\0\0\0\0WEBPVP8 ")
        self.assertEqual(self.run_import().problem, "")

    def test_dangling_cursor_link_dropped(self):
        snapshot(self.inbox, {"cursors/Snow/cursors/left_ptr": XCUR}, links={"cursors/Snow/cursors/hand": "nothere"})
        self.run_import()
        self.assertFalse((self.installed() / "cursors/Snow/cursors/hand").is_symlink())

    def test_second_import_replaces_and_cleans_old(self):
        snapshot(self.inbox)
        self.run_import()
        first = self.installed().resolve()
        (self.inbox / "snapshot/accounts").mkdir()
        (self.inbox / "snapshot/accounts/ada.png").write_bytes(PNG)
        r = self.run_import()
        self.assertEqual(r.problem, "")
        self.assertNotEqual(self.installed().resolve(), first)
        self.assertFalse(first.exists())
        self.assertEqual(sorted(p.name for p in self.dest.iterdir() if not p.name.startswith("snap-")), ["current"])

    def test_symlinked_file_refused(self):
        secret = self.root / "secret"
        secret.write_text("x")
        snapshot(self.inbox, links={"accounts": str(self.root)})
        r = self.run_import()
        self.assertEqual(r.problem, "")
        self.assertFalse((self.installed() / "accounts").exists())
        snap = self.inbox / "snapshot"
        (snap / "background.jpg").unlink()
        (snap / "background.jpg").symlink_to(secret)
        r = self.run_import()
        self.assertIn("background", r.problem)

    def test_cursor_alias_links_kept_inside_their_folder(self):
        snapshot(self.inbox, {"cursors/Snow/cursors/left_ptr": XCUR},
                 links={"cursors/Snow/cursors/default": "left_ptr", "cursors/Snow/cursors/evil": "../../../theme.json"})
        r = self.run_import()
        self.assertEqual(r.problem, "")
        cur = self.installed() / "cursors/Snow/cursors"
        self.assertEqual(os.readlink(cur / "default"), "left_ptr")
        self.assertFalse((cur / "evil").exists() or (cur / "evil").is_symlink())

    def test_wrong_magic_refused_file_by_file(self):
        snapshot(self.inbox, {"accounts/ada.png": b"#!/bin/sh\n", "fonts/x.ttf": b"nope"})
        r = self.run_import()
        self.assertEqual(r.problem, "")
        self.assertFalse((self.installed() / "accounts/ada.png").exists())
        self.assertIn("accounts/ada.png", r.skipped)
        self.assertIn("fonts/x.ttf", r.skipped)

    def test_unknown_paths_skipped(self):
        snapshot(self.inbox, {"run.sh": b"echo", "accounts/../x.png": PNG, "deep/a/b/c.png": PNG})
        r = self.run_import()
        self.assertEqual(r.problem, "")
        names = {str(p.relative_to(self.installed().resolve())) for p in self.installed().resolve().rglob("*")}
        self.assertNotIn("run.sh", names)
        self.assertFalse(any("deep" in n for n in names))

    def test_bad_theme_json_refused_and_old_kept(self):
        snapshot(self.inbox)
        self.run_import()
        good = self.installed().resolve()
        (self.inbox / "snapshot/theme.json").write_text(json.dumps({**THEME, "schema": "other"}))
        r = self.run_import()
        self.assertIn("schema", r.problem)
        self.assertEqual(self.installed().resolve(), good)

    def test_missing_referenced_background_refused(self):
        snapshot(self.inbox)
        (self.inbox / "snapshot/background.jpg").unlink()
        self.assertIn("background", self.run_import().problem)

    def test_size_limits(self):
        snapshot(self.inbox, {"accounts/big.png": PNG + b"\0" * (sync.LIMITS["accounts"] + 1)})
        r = self.run_import()
        self.assertIn("accounts/big.png", r.skipped)

    def test_total_limit_refuses_whole_snapshot(self):
        snapshot(self.inbox)
        old = sync.TOTAL
        sync.TOTAL = 10
        try:
            self.assertIn("total", self.run_import().problem)
        finally:
            sync.TOTAL = old

    def test_missing_snapshot_refused(self):
        self.assertIn("reader", self.run_import().problem)

    def test_json_is_rewritten(self):
        snapshot(self.inbox, {"theme.json": b'{"schema":"mavernix-greeter.theme","version":1,"id":"a","background":{"image":"background.jpg"}}   '})
        self.run_import()
        self.assertEqual((self.installed() / "theme.json").read_text(), json.dumps(
            {"schema": "mavernix-greeter.theme", "version": 1, "id": "a", "background": {"image": "background.jpg"}},
            indent=1, sort_keys=True) + "\n")


class Hostile(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.dest = self.root / "theme"

    def stream(self, members, links=()):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as t:
            for name, data in members:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
            for name, target in links:
                info = tarfile.TarInfo(name)
                info.type = tarfile.SYMTYPE
                info.linkname = target
                t.addfile(info)
        buf.seek(0)
        return buf

    def test_entry_count_capped(self):
        members = [(f"accounts/u{i}.png", PNG) for i in range(sync.MAX_ENTRIES + 1)]
        with self.assertRaisesRegex(ValueError, "entries"):
            sync.read_stream(self.stream(members))

    def test_skipped_names_also_count(self):
        members = [(f"junk/{i}", b"x") for i in range(sync.MAX_ENTRIES + 1)]
        with self.assertRaisesRegex(ValueError, "entries"):
            sync.read_stream(self.stream(members))

    def test_deep_json_refused_not_crashing(self):
        deep = b"[" * 100000 + b"]" * 100000
        theme, problem = sync.check_theme({"theme.json": deep})
        self.assertIsNone(theme)
        self.assertIn("theme.json", problem)

    def test_file_and_link_with_one_name_installs_the_file(self):
        theme = json.loads(json.dumps(THEME))
        files = {"background.jpg": JPG, "cursors/S/cursors/a": XCUR, "cursors/S/cursors/b": XCUR}
        new = sync.install(self.dest, theme, files, {"cursors/S/cursors/a": "b"})
        self.assertFalse((new / "cursors/S/cursors/a").is_symlink())

    def test_failed_install_leaves_nothing_behind(self):
        theme = json.loads(json.dumps(THEME))
        with self.assertRaises(Exception):
            sync.install(self.dest, theme, {"background.jpg": JPG, "x/../../escape": b"1"}, {})
        self.assertEqual([p.name for p in self.dest.iterdir() if p.name.startswith("snap-")], [])

    def test_same_content_not_installed_twice(self):
        inbox = self.root / "inbox"
        snapshot(inbox)
        reader = [sys.executable, "-I", str(Path(sync.__file__).with_name("reader.py"))]
        first = sync.import_snapshot(inbox / "snapshot", self.dest, reader=reader)
        again = sync.import_snapshot(inbox / "snapshot", self.dest, reader=reader)
        self.assertEqual(again.problem, "")
        self.assertEqual(again.installed, None)
        self.assertEqual(self.dest.joinpath("current").resolve(), first.installed)

    def test_reset_empties_but_keeps_the_folder(self):
        sync.install(self.dest, json.loads(json.dumps(THEME)), {"background.jpg": JPG}, {})
        sync.reset(self.dest)
        self.assertTrue(self.dest.is_dir())
        self.assertEqual(list(self.dest.iterdir()), [])


class Stream(unittest.TestCase):
    def test_tar_member_types_checked(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as t:
            info = tarfile.TarInfo("theme.json")
            info.type = tarfile.CHRTYPE
            t.addfile(info)
        buf.seek(0)
        files, links, skipped = sync.read_stream(buf)
        self.assertEqual(files, {})
        self.assertIn("theme.json", skipped)


if __name__ == "__main__":
    unittest.main()
