import os
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path

from mavernix_greeter import users

Pw = namedtuple("Pw", "pw_name pw_uid pw_gecos pw_shell")


class Users(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.icons = self.root / "icons"
        self.icons.mkdir()
        self.shells = {"/bin/bash", "/usr/bin/zsh"}
        self.limits = (1000, 60000)

    def listing(self, entries, **kw):
        kw.setdefault("hidden", ())
        return users.listing(entries, self.limits, self.shells, self.icons, **kw)

    def test_regular_user_listed_with_full_name(self):
        (u,) = self.listing([Pw("ada", 1000, "Ada Lovelace,,,", "/usr/bin/zsh")])
        self.assertEqual((u["name"], u["full_name"], u["uid"]), ("ada", "Ada Lovelace", 1000))

    def test_system_and_nologin_users_left_out(self):
        got = self.listing([Pw("root", 0, "", "/bin/bash"), Pw("greeter", 949, "", "/bin/bash"),
                            Pw("nobody", 65534, "", "/bin/bash"), Pw("svc", 1001, "", "/usr/bin/nologin"),
                            Pw("ok", 1002, "", "/bin/bash")])
        self.assertEqual([u["name"] for u in got], ["ok"])

    def test_shell_must_be_listed(self):
        self.assertEqual(self.listing([Pw("a", 1000, "", "/bin/fish")]), [])

    def test_nologin_left_out_even_when_listed(self):
        self.shells.add("/usr/bin/nologin")
        self.assertEqual(self.listing([Pw("a", 1000, "", "/usr/bin/nologin")]), [])

    def test_hidden_users_left_out(self):
        got = self.listing([Pw("a", 1000, "", "/bin/bash"), Pw("b", 1001, "", "/bin/bash")], hidden=("a",))
        self.assertEqual([u["name"] for u in got], ["b"])

    def test_empty_gecos_falls_back_to_name(self):
        (u,) = self.listing([Pw("ada", 1000, "", "/bin/bash")])
        self.assertEqual(u["full_name"], "ada")

    def test_avatar_only_regular_small_file(self):
        (self.icons / "a").write_bytes(b"\x89PNG")
        (self.icons / "b").symlink_to(self.icons / "a")
        (self.icons / "c").write_bytes(b"x" * (users.MAX_AVATAR + 1))
        got = self.listing([Pw(n, 1000 + i, "", "/bin/bash") for i, n in enumerate("abcd")])
        self.assertEqual([u["avatar"] for u in got], [str(self.icons / "a"), "", "", ""])

    def test_sorted_by_uid(self):
        got = self.listing([Pw("z", 1000, "", "/bin/bash"), Pw("a", 1001, "", "/bin/bash")])
        self.assertEqual([u["name"] for u in got], ["z", "a"])

    def test_login_defs_limits(self):
        p = self.root / "login.defs"
        p.write_text("# x\nUID_MIN\t\t 1500\nUID_MAX 2000\nOTHER 3\n")
        self.assertEqual(users.uid_limits(p), (1500, 2000))
        self.assertEqual(users.uid_limits(self.root / "missing"), (1000, 60000))

    def test_shells_file(self):
        p = self.root / "shells"
        p.write_text("# c\n/bin/sh\n\n/usr/bin/zsh\n")
        self.assertEqual(users.shells(p), {"/bin/sh", "/usr/bin/zsh"})


if __name__ == "__main__":
    unittest.main()
