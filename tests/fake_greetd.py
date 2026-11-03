#!/usr/bin/env python3
"""fake_greetd.py SOCKET SCENARIO LOG: speaks greetd IPC with scripted PAM conversations."""
import json
import os
import socket
import struct
import sys
import time

SCENARIOS = {
    "password": [("secret", "Password: ", "right")],
    "u2f": [("info", "Please touch the device.", None)],
    "u2f_then_password": [("info", "Please touch the device.", None), ("secret", "Password: ", "right")],
    "multi": [("secret", "Password: ", "right"), ("visible", "Verification code: ", "123456")],
    "expired": [("secret", "Password: ", "right"), ("error", "Your password has expired.", None),
                ("secret", "New password: ", "next"), ("secret", "Retype new password: ", "next")],
    "fail_start": [("secret", "Password: ", "right")],
    "slow": [("secret", "Password: ", "right")],
}


def send(conn, obj):
    data = json.dumps(obj).encode()
    conn.sendall(struct.pack("=I", len(data)) + data)


def recv(conn):
    head = conn.recv(4, socket.MSG_WAITALL)
    if len(head) < 4:
        return None
    (n,) = struct.unpack("=I", head)
    return json.loads(conn.recv(n, socket.MSG_WAITALL))


class Greetd:
    def __init__(self, scenario, log):
        self.scenario, self.log = scenario, log
        self.steps, self.user, self.ok = None, None, True

    def note(self, **kv):
        line = "[fake-greetd] " + " ".join(f"{k}={v}" for k, v in kv.items())
        with open(self.log, "a") as f:
            f.write(line + "\n")

    def next_message(self):
        while self.steps:
            kind, text, _ = self.steps[0]
            if kind in ("info", "error"):
                self.steps.pop(0)
                return {"type": "auth_message", "auth_message_type": kind, "auth_message": text}, True
            return {"type": "auth_message", "auth_message_type": kind, "auth_message": text}, False
        return None, False

    def reply_after_answer(self):
        msg, needs_ack = self.next_message()
        if msg:
            self.pending_ack = needs_ack
            return msg
        if not self.ok:
            self.steps = None
            return {"type": "error", "error_type": "auth_error", "description": "pam_authenticate: AUTH_ERR"}
        self.steps = []
        return {"type": "success"}

    def handle(self, req):
        t = req.get("type")
        if t == "create_session":
            if self.steps is not None and self.steps != []:
                self.note(event="create", result="busy")
                return {"type": "error", "error_type": "error", "description": "a session is already being configured"}
            self.user, self.steps, self.ok = req["username"], list(SCENARIOS[self.scenario]), True
            self.pending_ack = False
            self.note(event="create", user=self.user)
            return self.reply_after_answer()
        if t == "post_auth_message_response":
            if self.steps is None:
                return {"type": "error", "error_type": "error", "description": "no session active"}
            answer = req.get("response")
            if self.pending_ack:
                self.pending_ack = False
                self.note(event="ack")
            else:
                _, text, want = self.steps.pop(0)
                self.ok = self.ok and answer == want
                self.note(event="answer", prompt=json.dumps(text), length=len(answer or ""))
            return self.reply_after_answer()
        if t == "cancel_session":
            self.steps = None
            self.note(event="cancel")
            return {"type": "success"}
        if t == "start_session":
            if self.steps != []:
                self.note(event="start", result="not_authenticated")
                return {"type": "error", "error_type": "error", "description": "session not authenticated"}
            if self.scenario == "fail_start":
                self.scenario, self.steps = "password", None
                self.note(event="start", result="failed")
                return {"type": "error", "error_type": "error", "description": "exec failed"}
            self.note(event="start", user=self.user, cmd=json.dumps(req.get("cmd")), env=json.dumps(req.get("env")))
            return {"type": "success"}
        return {"type": "error", "error_type": "error", "description": "unknown request"}


def main():
    path, scenario, log = sys.argv[1:4]
    g = Greetd(scenario, log)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(4)
    srv.settimeout(int(os.environ.get("FAKE_GREETD_LIMIT", "120")))
    g.note(event="listening", scenario=scenario)
    while True:
        try:
            conn, _ = srv.accept()
        except TimeoutError:
            g.note(event="timeout")
            return 2
        g.note(event="connected")
        while (req := recv(conn)) is not None:
            if scenario == "slow":
                time.sleep(0.5)
            send(conn, g.handle(req))
        g.note(event="disconnected")
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
