#!/usr/bin/env bash
# migrate_test.sh OUT runs the migration tool against stand in units inside the test container
set -uo pipefail
out=$1
mkdir -p "$out"
exec > "$out/migrate.log" 2>&1
m=/usr/lib/mavernix-greeter/migrate
fail() { echo "[e2e] result=fail reason=$*"; exit 1; }
dm() { basename "$(readlink -f /etc/systemd/system/display-manager.service)"; }

cat > /etc/systemd/system/oldlogin.service <<'U'
[Service]
ExecStart=/bin/true
[Install]
Alias=display-manager.service
U
printf 'auth required pam_permit.so\n#marker-oldlogin\n' > /etc/pam.d/oldlogin
systemctl enable oldlogin.service || fail "could not enable stand in"
[[ $(dm) == oldlogin.service ]] || fail "stand in not the display manager"
pam_before=$(sha256sum /etc/pam.d/greetd | cut -d' ' -f1)

$m preflight || fail "preflight found problems"
$m cutover && fail "cutover ran before stage"
$m stage --pam-from '../shadow' && fail "bad pam name accepted"
$m stage --pam-from oldlogin || fail "stage failed"
[[ $(dm) == oldlogin.service ]] || fail "stage switched the display manager"
grep -q marker-oldlogin /etc/pam.d/greetd || fail "pam stack not copied"
grep -q /usr/lib/mavernix-greeter/greeter-session /etc/greetd/config.toml || fail "config not written"
$m cutover || fail "cutover failed"
[[ $(dm) == greetd.service ]] || fail "cutover did not switch, dm=$(dm)"
systemctl is-enabled oldlogin.service && fail "old display manager still enabled"
$m rollback || fail "rollback failed"
[[ $(dm) == oldlogin.service ]] || fail "rollback did not restore, dm=$(dm)"
systemctl is-enabled greetd.service && fail "greetd still enabled after rollback"
[[ $(sha256sum /etc/pam.d/greetd | cut -d' ' -f1) == "$pam_before" ]] || fail "pam file not restored"
echo "[e2e] result=pass stage cutover rollback"
