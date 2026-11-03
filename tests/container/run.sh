#!/usr/bin/env bash
# run.sh OUT_DIR drives the installed greeter against real greetd in a fresh container
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=$1 base=${BASE:-exp-greetd-base} name=exp-greetd-run
ulimit -c 0
[[ $(ulimit -c) == 0 ]] || { echo "[container] refused reason=core_limit"; exit 2; }
mkdir -p "$out"
work=$(mktemp -d "${TMPDIR:-/tmp}/ct.XXXXXX")
trap 'rm -rf "$work"; machinectl --user remove "$name" >/dev/null 2>&1' EXIT
machinectl --user remove "$name" >/dev/null 2>&1
machinectl --user clone "$base" "$name" || { echo "[container] refused reason=clone"; exit 2; }
timeout 120 meson setup "$work/build" "$repo" --prefix=/usr --libexecdir=lib >/dev/null || exit 2
timeout 120 meson install -C "$work/build" --destdir "$work/dest" >/dev/null || exit 2
cc -O2 -shared -fPIC -o "$work/dest/usr/local/lib/nomlock.so" "$here/nomlock.c" 2>/dev/null || {
  mkdir -p "$work/dest/usr/local/lib" && cc -O2 -shared -fPIC -o "$work/dest/usr/local/lib/nomlock.so" "$here/nomlock.c"; }
mkdir -p "$work/dest/test"
cp "$here/setup.sh" "$here/e2e.py" "$work/dest/test/"
pw=$(head -c 12 /dev/urandom | od -An -tx1 | tr -dc 'a-f' | head -c 12)
[[ ${#pw} -ge 6 ]] || pw=correcthorse
printf '%s' "$pw" > "$work/dest/test/pw"
chmod 600 "$work/dest/test/pw"
start=$(date '+%F %T')
tar -C "$work/dest" -c . | timeout 300 systemd-nspawn -q --machine="$name" --pipe bash -c \
  "ulimit -c 0; tar -C / -x --no-same-owner && bash /test/setup.sh >&2 && python3 /test/e2e.py /var/tmp/out >&2; rc=\$?; tar -C /var/tmp/out -c . ; exit \$rc" \
  > "$work/out.tar" 2> "$out/nspawn.log"
rc=$?
tar -C "$out" -xf "$work/out.tar" || { echo "[container] results unreadable"; rc=1; }
grep -q '^\[e2e\] result=pass' "$out/e2e.log" 2>/dev/null || { echo "[container] no pass line in e2e.log"; rc=1; }
if grep -rq -- "$pw" "$out"; then echo "[container] password found in collected logs"; rc=1; fi
dumps=$(coredumpctl list --since "$start" --no-pager 2>/dev/null | grep -cE 'greetd|wayfire|quickshell' || true)
grep -h '^\[e2e\]' "$out/e2e.log" 2>/dev/null
echo "[container] exit=$rc coredumps=$dumps out=$out"
exit $rc
