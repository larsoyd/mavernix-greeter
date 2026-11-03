#!/usr/bin/env bash
# session_run.sh OUT_DIR [case...] tests the greeter session script headless
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ulimit -c 0
[[ $(ulimit -c) == 0 ]] || { echo "[session] refused reason=core_limit"; exit 2; }
start=$(date '+%F %T')
setsid -w timeout -k 3 "${LIMIT:-150}" dbus-run-session --config-file="$here/bus.conf" -- python3 "$here/session_test.py" "$@"
rc=$?
dumps=$(coredumpctl list --since "$start" --no-pager 2>/dev/null | grep -cE 'wayfire|quickshell|qs ' || true)
echo "[session] exit=$rc coredumps=$dumps"
[[ $dumps == 0 ]] || rc=98
exit $rc
