import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "src/session/text-greeter"
HINT = "The login screen could not start. Log in here to reach the desktop."


class TextGreeter(unittest.TestCase):
    def run_with(self, tools):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "bin").mkdir()
            (tmp / "lib").mkdir()
            (tmp / "lib" / "helper").write_text("#!/bin/sh\necho /usr/bin/start desk\n")
            (tmp / "lib" / "helper").chmod(0o755)
            for name in tools:
                tool = tmp / "bin" / name
                tool.write_text(f'#!/bin/sh\nprintf "%s\\n" {name} "$@"\n')
                tool.chmod(0o755)
            for name in ("bash", "env", "timeout"):
                (tmp / "bin" / name).symlink_to(f"/usr/bin/{name}")
            r = subprocess.run([str(SCRIPT)], env={"PATH": str(tmp / "bin"), "MAVERNIX_GREETER_LIBDIR": str(tmp / "lib")},
                               capture_output=True, text=True, timeout=20)
            return r.stdout.splitlines()

    def test_plain_login_says_why_it_is_shown(self):
        out = self.run_with(["agreety"])
        self.assertEqual(out, ["", HINT, "", "agreety", "--cmd", "/usr/bin/start desk"])

    def test_full_screen_login_carries_the_same_words(self):
        out = self.run_with(["agreety", "tuigreet"])
        self.assertEqual(out, ["tuigreet", "--time", "--remember", "--greeting", HINT, "--cmd", "/usr/bin/start desk"])


if __name__ == "__main__":
    unittest.main()
