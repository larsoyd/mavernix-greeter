#!/usr/bin/env bash
# harness.sh SCENARIO OUT_DIR runs one greeter in a private compositor
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
scenario=$1 out=$2
ulimit -c 0
[[ $(ulimit -c) == 0 ]] || { echo "[harness] refused reason=core_limit"; exit 2; }
command -v wayfire qs grim dbus-run-session >/dev/null || { echo "[harness] refused reason=missing_tools"; exit 2; }
mkdir -p "$out"
rt=$(mktemp -d "${TMPDIR:-/tmp}/gr.XXXXXX")
home=$(mktemp -d "${TMPDIR:-/tmp}/grh.XXXXXX")
trap 'rm -rf "$rt" "$home"' EXIT
export KDE_DEBUG=1 QT_FORCE_STDERR_LOGGING=1 QS_DISABLE_CRASH_HANDLER=1
export XDG_RUNTIME_DIR=$rt HOME=$home XDG_CONFIG_HOME=$home/c XDG_DATA_HOME=$home/d XDG_CACHE_HOME=$home/ca XDG_STATE_HOME=$home/s
export _WAYFIRE_SOCKET=$rt/wf.sock WLR_BACKENDS=headless WLR_RENDERER=${WLR_RENDERER:-pixman}
export WLR_HEADLESS_OUTPUTS=${OUTPUTS:-1} WLR_LIBINPUT_NO_DEVICES=1 PULSE_SERVER=unix:/nonexistent
unset DISPLAY WAYLAND_DISPLAY WAYLAND_SOCKET
export MAVENIX_GREETER_HELPER=$here/stub_helper.py STUB_RECORD=$out/helper.log
export MAVENIX_GREETER_THEME_DIR=${THEME_DIR:-$repo/data/themes/neutral}
if PYTHONPATH=$repo/src/helper python3 -c 'import sys; from mavenix_greeter import cli; sys.exit(cli.main(sys.argv[1:]))' \
  fontconfig --theme-dir "$MAVENIX_GREETER_THEME_DIR" --cache "$rt/fontconfig" > "$rt/fonts.conf"; then
  export FONTCONFIG_FILE=$rt/fonts.conf
fi
export SCENARIO=$scenario OUT=$out REPO=$repo HERE=$here RT=$rt
: > "$out/helper.log"; : > "$out/greetd.log"
start=$(date '+%F %T')
# shellcheck disable=SC2016
setsid -w timeout -k 3 "${LIMIT:-60}" dbus-run-session --config-file="$here/bus.conf" -- bash -c '
  wayfire -c "$HERE/compositor.ini" >"$OUT/wayfire.log" 2>&1 & w=$!
  trap "kill $w 2>/dev/null; sleep .3; kill -9 $w 2>/dev/null" EXIT
  WF_PID=$w python3 "$HERE/driver.py"
  rc=$?
  kill -0 $w 2>/dev/null || { echo "[harness] compositor died"; rc=99; }
  exit $rc'
rc=$?
dumps=$(coredumpctl list --since "$start" --no-pager 2>/dev/null | grep -cE 'wayfire|quickshell|qs ' || true)
echo "[harness] scenario=$scenario exit=$rc coredumps=$dumps out=$out"
[[ $dumps == 0 ]] || rc=98
exit $rc
