#!/usr/bin/env bash
# runs inside a fresh test container as its root
set -euo pipefail
ulimit -c 0
pw=$(cat /test/pw)
useradd -m -s /bin/bash -c "Ada Tester" ada
useradd -m -s /bin/bash -c "Bob Tester" bob
printf 'ada:%s\nbob:%s\n' "$pw" "$pw-bob" | chpasswd
install -d -m 1777 /var/tmp/runs
cat > /usr/local/bin/test-session <<'S'
#!/usr/bin/env bash
printf '%s user=%s type=%s desktop=%s class=%s\n' "$(date +%s.%N)" "$USER" "${XDG_SESSION_TYPE:-}" \
  "${XDG_SESSION_DESKTOP:-}" "${XDG_SESSION_CLASS:-}" >> /var/tmp/runs/sessions.log
sleep 1
S
cat > /usr/share/wayland-sessions/testsession.desktop <<'S'
[Desktop Entry]
Name=Test Session
Exec=/usr/local/bin/test-session
S
install -d /etc/mavernix-greeter
printf '[sessions]\ndefault = "testsession"\n' > /etc/mavernix-greeter/greeter.toml
cat > /usr/local/bin/wayfire-test <<'S'
#!/usr/bin/env bash
sed -i 's/^plugins = autostart$/plugins = autostart ipc stipc/' "$2"
exec wayfire "$@"
S
cat > /usr/local/bin/greeter-test-env <<'S'
#!/usr/bin/env bash
ulimit -c 0
export XDG_RUNTIME_DIR=/run/user/$(id -u) WLR_BACKENDS=headless WLR_RENDERER=pixman WLR_HEADLESS_OUTPUTS=1
export WLR_LIBINPUT_NO_DEVICES=1 _WAYFIRE_SOCKET=/run/user/$(id -u)/wf.sock WLR_DRM_DEVICES=none
export MAVERNIX_GREETER_COMPOSITOR=/usr/local/bin/wayfire-test QT_FORCE_STDERR_LOGGING=1
exec /usr/lib/mavernix-greeter/greeter-session
S
chmod +x /usr/local/bin/test-session /usr/local/bin/wayfire-test /usr/local/bin/greeter-test-env
cat > /etc/greetd/config.toml <<'S'
[terminal]
vt = "none"
[default_session]
command = "/usr/local/bin/greeter-test-env"
user = "greeter"
S
systemd-tmpfiles --create /usr/lib/tmpfiles.d/mavernix-greeter.conf
install -d -m 700 -o greeter -g greeter "/run/user/$(id -u greeter)"
echo "[setup] done"
