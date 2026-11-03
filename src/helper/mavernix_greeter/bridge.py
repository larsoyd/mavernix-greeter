import json
import os
import select
import socket
import struct
import sys

BUSY = "a session is already being configured"


def request(kind, msg, internal=False):
    return {"kind": kind, "msg": msg, "internal": internal}


CANCEL = {"type": "cancel_session"}


# one request in flight, so every answer from greetd meets the request it belongs to
class Bridge:
    def __init__(self):
        self.sent, self.events = [], []
        self.queue, self.outstanding = [], None
        self.prompt_open = self.ready = self.stale = False

    def emit(self, ev, **kw):
        self.events.append({"ev": ev, **kw})

    def pump(self):
        if self.outstanding is None and self.queue:
            self.outstanding = self.queue.pop(0)
            self.sent.append(self.outstanding["msg"])

    def ui(self, op):
        kind = op.get("op")
        if kind == "create" and isinstance(op.get("user"), str):
            self.queue.append(request("create", {"type": "create_session", "username": op["user"]}))
        elif kind == "respond" and self.prompt_open and isinstance(op.get("value"), str):
            self.prompt_open = False
            self.queue.append(request("answer", {"type": "post_auth_message_response", "response": op["value"]}))
        elif kind == "cancel":
            self.prompt_open = self.ready = False
            self.queue = [r for r in self.queue if r["kind"] == "cancel"]
            if self.outstanding and self.outstanding["kind"] != "cancel":
                self.stale = True
            if not any(r["kind"] == "cancel" for r in self.queue):
                self.queue.append(request("cancel", CANCEL))
        elif kind == "start":
            if not self.ready:
                self.emit("error", stage="launch", text="not authenticated")
                return
            self.ready = False
            self.queue.append(request("start", {"type": "start_session", "cmd": list(op.get("cmd", [])),
                                                "env": list(op.get("env", []))}))
        self.pump()

    def cleanup_first(self, *after):
        self.queue[:0] = [request("cancel", CANCEL, internal=True), *after]

    def greetd(self, resp):
        o, self.outstanding = self.outstanding, None
        if o is None:
            self.pump()
            return
        if self.stale and o["kind"] != "cancel":
            self.stale = False
        elif o["kind"] == "start":
            if resp.get("type") == "success":
                self.emit("launched")
            else:
                self.emit("error", stage="launch", text=str(resp.get("description", "")))
                self.cleanup_first()
        elif o["kind"] != "cancel":
            self.talk(o, resp)
        self.pump()

    def talk(self, o, resp):
        t = resp.get("type")
        if t == "auth_message":
            mtype = resp.get("auth_message_type")
            self.emit("message", kind=mtype, text=str(resp.get("auth_message", "")))
            if mtype in ("info", "error"):
                self.queue.insert(0, request("ack", {"type": "post_auth_message_response", "response": None}))
            else:
                self.prompt_open = True
        elif t == "success":
            self.ready = True
            self.emit("ready")
        elif t == "error" and o["kind"] == "create" and resp.get("description") == BUSY:
            self.cleanup_first(o)
        elif t == "error":
            stage = "auth" if resp.get("error_type") == "auth_error" else "service"
            self.emit("failure" if stage == "auth" else "error", stage=stage, text=str(resp.get("description", "")))
            self.cleanup_first()


def log(text):
    print(f"[bridge] {text}", file=sys.stderr, flush=True)


def send_events(bridge, out):
    for e in bridge.events:
        out.write(json.dumps(e) + "\n")
    out.flush()
    bridge.events = []


def send_requests(bridge, sock):
    for r in bridge.sent:
        data = json.dumps(r).encode()
        sock.sendall(struct.pack("=I", len(data)) + data)
        log(f"sent type={r['type']}")
    bridge.sent = []


def read_reply(sock, buf):
    chunk = sock.recv(65536)
    if not chunk:
        return None
    buf += chunk
    replies = []
    while len(buf) >= 4:
        (n,) = struct.unpack("=I", buf[:4])
        if len(buf) < 4 + n:
            break
        replies.append(json.loads(buf[4:4 + n]))
        del buf[:4 + n]
    return replies


def main(stdin=sys.stdin, out=sys.stdout):
    path = os.environ.get("GREETD_SOCK", "")
    bridge = Bridge()
    if not path:
        bridge.emit("unavailable")
        send_events(bridge, out)
        return 1
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(path)
    except OSError as e:
        bridge.emit("unavailable")
        send_events(bridge, out)
        log(f"connect failed error={e.__class__.__name__}")
        return 1
    bridge.emit("connected")
    send_events(bridge, out)
    buf, inbuf = bytearray(), b""
    fd = stdin.fileno()
    while True:
        ready, _, _ = select.select([fd, sock], [], [])
        if sock in ready:
            replies = read_reply(sock, buf)
            if replies is None:
                bridge.emit("lost")
                send_events(bridge, out)
                log("greetd closed the connection")
                return 1
            for r in replies:
                log(f"reply type={r.get('type')} kind={r.get('auth_message_type', r.get('error_type', ''))}")
                bridge.greetd(r)
        if fd in ready:
            chunk = os.read(fd, 65536)
            if not chunk:
                return 0
            inbuf += chunk
            while b"\n" in inbuf:
                line, inbuf = inbuf.split(b"\n", 1)
                try:
                    bridge.ui(json.loads(line))
                except ValueError:
                    log("refused unreadable command")
        send_requests(bridge, sock)
        send_events(bridge, out)
