import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mavernix_greeter import cli


def call(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(list(argv))
    return rc, buf.getvalue()


class Main(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_compositor_reads_theme_dir(self):
        (self.d / "theme.json").write_text(json.dumps({"cursor": {"theme": "Snow", "size": 32}}))
        rc, out = call("compositor", "--theme-dir", str(self.d), "--client", "/x/run")
        self.assertEqual(rc, 0)
        self.assertIn("cursor_theme = Snow", out)
        self.assertIn("greeter = /x/run", out)

    def test_compositor_without_theme_still_works(self):
        rc, out = call("compositor", "--theme-dir", str(self.d / "none"), "--client", "/x/run")
        self.assertEqual(rc, 0)
        self.assertIn("plugins = autostart", out)

    def test_other_offered_only_when_someone_is_hidden(self):
        import pwd
        me = pwd.getpwuid(__import__("os").getuid()).pw_name
        conf = self.d / "g.toml"
        conf.write_text("[users]\nhidden = []\n")
        rc, out = call("--config", str(conf), "users")
        self.assertEqual(json.loads(out)["offer_other"], not json.loads(out)["users"])
        conf.write_text('[users]\nhidden = ["somebody-else"]\n')
        rc, out = call("--config", str(conf), "users")
        self.assertTrue(json.loads(out)["offer_other"])

    def test_remember_and_users_last(self):
        state = self.d / "last.json"
        rc, _ = call("--state", str(state), "remember", "ada", "wayfire")
        self.assertEqual(rc, 0)
        rc, out = call("--state", str(state), "--config", str(self.d / "none.toml"), "users")
        self.assertEqual(json.loads(out)["last"], {"user": "ada", "session": "wayfire"})


if __name__ == "__main__":
    unittest.main()
