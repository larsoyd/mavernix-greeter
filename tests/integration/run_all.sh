#!/usr/bin/env bash
# run_all.sh OUT_DIR [scenario...]: every greeter scenario, one private compositor each
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=$1; shift
all=(password_ok wrong_then_ok u2f u2f_then_password_typed_early multi expired fail_start pick_second_user cancel_during_touch unavailable greetd_dies two_outputs)
(( $# )) && all=("$@")
fails=0
for s in "${all[@]}"; do
  env=()
  [[ $s == two_outputs ]] && env=(OUTPUTS=2)
  env "${env[@]}" LIMIT=45 bash "$here/harness.sh" "$s" "$out/$s" 2>/dev/null | grep -E '^\[(driver|harness)\]'
  (( PIPESTATUS[0] == 0 )) || fails=$((fails + 1))
done
echo "[integration] scenarios=${#all[@]} failed=$fails"
(( fails == 0 ))
