#!/usr/bin/env python3
import json
import os
import sys

if sys.argv[1] == "bridge":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src", "helper"))
    from mavernix_greeter import bridge
    sys.exit(bridge.main())

record = os.environ["STUB_RECORD"]
users = [{"name": n, "full_name": n.title() + " Tester", "uid": 1000 + i, "avatar": ""}
         for i, n in enumerate(os.environ.get("STUB_USERS", "ada").split(",")) if n]
sessions = [{"id": "mavernix", "name": "Mavernix", "type": "wayland", "argv": ["/usr/bin/start desk"],
             "cmd": ["'/usr/bin/start desk'"], "env": ["XDG_SESSION_TYPE=wayland"]},
            {"id": "wayfire", "name": "Wayfire", "type": "wayland", "argv": ["wayfire"], "cmd": ["wayfire"],
             "env": ["XDG_SESSION_TYPE=wayland"]}]
with open(record, "a") as f:
    f.write("[stub-helper] " + " ".join(sys.argv[1:]) + "\n")
cmd = sys.argv[1]
if cmd == "users":
    out = {"show_list": True, "users": users, "last": {}}
elif cmd == "sessions":
    out = {"sessions": [] if os.environ.get("STUB_SESSIONS") == "none" else sessions}
elif cmd == "power-caps":
    out = {"poweroff": True, "reboot": True, "suspend": False}
else:
    out = {"ok": True}
print(json.dumps(out))
