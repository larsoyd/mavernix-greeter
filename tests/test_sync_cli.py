import os
import tempfile
import unittest
from pathlib import Path

from mavenix_greeter import sync_cli


class Inbox(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.box = self.base / "inbox"
        self.box.mkdir(mode=0o755)
        self.me = os.getuid()

    def test_owned_user_dir_accepted(self):
        (self.box / "ada").mkdir(mode=0o700)
        self.assertEqual(sync_cli.check_inbox(self.box, "ada", self.me, root_uid=self.me), "")

    def test_wrong_owner_refused(self):
        (self.box / "ada").mkdir(mode=0o700)
        self.assertIn("owner", sync_cli.check_inbox(self.box, "ada", self.me + 1, root_uid=self.me))

    def test_symlinked_user_dir_refused(self):
        (self.box / "ada").symlink_to(self.base)
        self.assertIn("directory", sync_cli.check_inbox(self.box, "ada", self.me, root_uid=self.me))

    def test_writable_inbox_root_refused(self):
        (self.box / "ada").mkdir()
        self.box.chmod(0o777)
        self.assertIn("inbox", sync_cli.check_inbox(self.box, "ada", self.me, root_uid=self.me))

    def test_inbox_root_owned_by_another_refused(self):
        (self.box / "ada").mkdir()
        self.assertIn("inbox", sync_cli.check_inbox(self.box, "ada", self.me, root_uid=self.me + 1))

    def test_bad_user_name_refused(self):
        self.assertIn("name", sync_cli.check_inbox(self.box, "../etc", self.me, root_uid=self.me))

    def test_reader_drops_to_user(self):
        cmd = sync_cli.reader_cmd(1000, 1000)
        self.assertEqual(cmd[:2], ["setpriv", "--reuid=1000"])
        self.assertIn("--no-new-privs", cmd)
        self.assertIn("--clear-groups", cmd)
        self.assertIn("-I", cmd)


if __name__ == "__main__":
    unittest.main()
