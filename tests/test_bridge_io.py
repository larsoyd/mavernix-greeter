import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src" / "helper"


class Live(unittest.TestCase):
    def start(self, scenario):
        self.dir = Path(tempfile.mkdtemp())
        sock = self.dir / "g.sock"
        self.log = self.dir / "g.log"
        self.fake = subprocess.Popen([sys.executable, HERE / "fake_greetd.py", sock, scenario, self.log],
                                     env={**os.environ, "FAKE_GREETD_LIMIT": "20"})
        for _ in range(100):
            if sock.exists():
                break
            time.sleep(0.05)
        self.br = subprocess.Popen([sys.executable, "-c", "import sys; from mavernix_greeter import bridge; sys.exit(bridge.main())"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   env={**os.environ, "GREETD_SOCK": str(sock), "PYTHONPATH": str(SRC)})
        self.assertEqual(self.next(), {"ev": "connected"})

    def tearDown(self):
        for p in (getattr(self, "br", None), getattr(self, "fake", None)):
            if p and p.poll() is None:
                p.kill()
                p.wait(5)
        if getattr(self, "br", None):
            for f in (self.br.stdin, self.br.stdout, self.br.stderr):
                f.close()

    def say(self, **op):
        self.br.stdin.write(json.dumps(op) + "\n")
        self.br.stdin.flush()

    def next(self):
        return json.loads(self.br.stdout.readline())

    def test_cancel_during_a_blocked_touch_then_password(self):
        self.start("u2f_then_password")
        self.say(op="create", user="ada")
        self.assertEqual(self.next()["kind"], "info")
        self.say(op="cancel")
        self.say(op="create", user="ada")
        e = self.next()
        self.assertEqual((e["ev"], e["kind"]), ("message", "info"), "a fresh login, not a leftover answer")
        e = self.next()
        self.assertEqual((e["ev"], e["kind"]), ("message", "secret"))
        self.say(op="respond", value="right")
        self.assertEqual(self.next(), {"ev": "ready"})
        self.say(op="start", cmd=["x"], env=[])
        self.assertEqual(self.next(), {"ev": "launched"})
        self.assertIn("event=cancel", self.log.read_text())

    def test_greetd_gone_is_reported(self):
        self.start("password")
        self.fake.kill()
        self.fake.wait(5)
        self.say(op="create", user="ada")
        self.assertEqual(self.next(), {"ev": "lost"})

    def test_no_socket_is_unavailable(self):
        br = subprocess.run([sys.executable, "-c", "import sys; from mavernix_greeter import bridge; sys.exit(bridge.main())"],
                            input="", capture_output=True, text=True, timeout=10,
                            env={**{k: v for k, v in os.environ.items() if k != "GREETD_SOCK"}, "PYTHONPATH": str(SRC)})
        self.assertEqual(json.loads(br.stdout), {"ev": "unavailable"})


if __name__ == "__main__":
    unittest.main()
