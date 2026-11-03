# mavenix-greeter

A graphical login screen for [greetd](https://sr.ht/~kennylevinsen/greetd/). The interface is written in
QML for [Quickshell](https://quickshell.org) and runs inside its own small [Wayfire](https://wayfire.org)
compositor, under greetd's unprivileged `greeter` account.

It works on its own with a neutral grey look. Installed next to the [Mavernix](https://github.com/larsoyd/mavernix)
desktop, it takes that desktop's wallpaper, fonts, cursor, keyboard layout and screen arrangement, so logging in
feels like one system.

The layout is modelled on the OS X 10.9 login window: a centred row of users, the chosen one sliding to the
middle, a damped shake on a wrong password, and Sleep, Restart and Shut Down at the bottom. No Apple artwork or
fonts are part of this project. A desktop theme you installed yourself can supply them.

## What it does

- Lists users from the password database (and AccountsService pictures), or asks for a name.
- Talks to greetd for everything about authentication. Any PAM conversation works: passwords, several prompts in a
  row, password changes, one-time codes and security keys that only need a touch. The screen never checks a
  password itself and never stores or logs what you type.
- Lists Wayland sessions, and X11 sessions when `xinit` is installed, from their desktop entries. The last user
  and session are remembered.
- Sleep, Restart and Shut Down through logind, only when logind allows them for the login screen.
- Shows the login on the main screen and the background on every other screen.
- Falls back on its own: a crashed interface is restarted twice, after that greetd's text login takes over on the
  same console. A desktop look that never got the screen to show three times running is set aside.

## Requirements

Checked with greetd 0.10.3, Quickshell 0.3.2, Wayfire 0.11.0 (wlroots 0.20), Python 3.14 and Qt 6.12 on Arch
Linux. systemd-logind is required. `greetd-agreety` (pulled in by greetd) or `greetd-tuigreet` provides the text
fallback.

## Install

On Arch Linux, build the package from `packaging/arch`:

    cd packaging/arch && makepkg -si

Or install by hand:

    meson setup build --prefix=/usr --libexecdir=lib
    meson compile -C build
    meson test -C build
    sudo meson install -C build

Installing does not change your login screen. Switching is a separate step.

## Switching to it

`/usr/lib/mavenix-greeter/migrate` does this in steps. Every step prints `[migrate] key=value` lines and refuses
rather than guessing.

1. `migrate preflight` checks greetd, the `greeter` account, the text fallback, that at least one session is found
   and that text consoles are available. It changes nothing.
2. `sudo migrate stage --pam-from <service>` writes `/etc/greetd/config.toml` and, with `--pam-from`, copies the
   PAM stack of your current login manager to `/etc/pam.d/greetd`, so security keys, faillock and wallet unlocking
   keep working. Everything it replaces is saved under `/var/backups/mavenix-greeter/<time>/`. The active login
   manager is not touched.
3. `sudo migrate cutover` disables the current display manager and enables `greetd.service`. It takes effect at the
   next boot. Nothing running is stopped.
4. `sudo migrate rollback` restores the saved files and re-enables the previous display manager.

Before the first real boot, make sure you know your way to a text console (Ctrl+Alt+F2 to F6).

## Desktop look (Mavernix and others)

The login screen never reads anything in a home folder. A desktop hands its look over through an inbox:

    sudo mavenix-greeter-sync enable <user>

This makes `/var/lib/mavenix-greeter/inbox/<user>/`, owned by that user, and enables
`mavenix-greeter-sync@<user>.path`. Mavernix writes a snapshot there at login and after display or keyboard
changes. The sync service reads the snapshot with that user's own permissions, checks every file by name, type,
size and content, and installs it atomically to `/var/lib/mavenix-greeter/theme/current`.
`sudo mavenix-greeter-sync reset` goes back to the neutral look, `disable <user>` stops taking updates.

Whoever is enabled here decides what the login screen looks like for everyone, so only enable trusted accounts.

### Snapshot format, version 1

A folder with `theme.json` and the files it names:

| key | meaning |
|---|---|
| `schema`, `version` | `"mavenix-greeter.theme"` and `1`. Other values are refused. |
| `id`, `name` | the desktop theme's id and display name |
| `background` | `image` (`background.png/.jpg/.webp`), `fit` (`cover`, `contain`, `stretch`), `veil`, or `color`, `color2`, `center_y`, `radius_x`, `radius_y` for the radial gradient |
| `fonts` | `family`, `size`. Font files go in `fonts/` (ttf, otf, ttc, dfont). |
| `cursor` | `theme`, `size`. The cursor files go in `cursors/<theme>/cursors/`. |
| `keyboard` | xkb `layout`, `model`, `variant`. Options always come from the system keymap. |
| `display` | `outputs` (`name`, `mode`, `position`, `scale`, `transform`), `main_output`, `drm_driver` |
| `colors`, `avatar`, `tile`, `field`, `layout`, `animation` | finer look, `src/greeter/Theme.js` lists every key and its default |
| `accounts` | `{"<user>": {"avatar": "accounts/<user>.png"}}` |

Colours are `#rrggbbaa`. Unknown keys are ignored, missing ones take the neutral default, numbers are clamped and
asset paths must stay inside the snapshot. A theme cannot switch screens off. Newer schema versions will keep
reading version 1.

## Configuration

`/etc/mavenix-greeter/greeter.toml`:

    [users]
    hidden = []          # names left out of the list
    show_list = true     # false asks for a name instead

    [sessions]
    default = "mavernix" # desktop entry id used before anyone logged in

## Troubleshooting at boot

- **Black screen or text login instead of the greeter.** Switch to another console with Ctrl+Alt+F2, log in, and
  read `journalctl -b -t mavenix-greeter` and `journalctl -b -u greetd`. Lines start with `[greeter-session]`,
  `[run-greeter]` or `[greeter]` and give the reason.
- **To get the old login screen back.** From a text console run `sudo /usr/lib/mavenix-greeter/migrate rollback`,
  then reboot. Without the tool: `sudo systemctl disable greetd && sudo systemctl enable <old>.service`.
- **The look is broken.** `sudo mavenix-greeter-sync reset` brings back the neutral look.
- **Nothing works.** greetd gives up after five failed starts in 30 seconds. Text consoles keep working, since
  greetd only takes the first one.

## Uninstall

Run `migrate rollback` first, then remove the package. The package warns if greetd still points at it.
`/var/lib/mavenix-greeter` holds the imported look and the remembered last user and can be deleted afterwards.

## Development

    PYTHONPATH=src/helper python3 -m unittest discover -s tests   # helper, sync, sessions
    node --test tests/*.mjs                                        # login state machine, theme, layout
    bash tests/integration/run_all.sh OUT_DIR                      # the real QML greeter, headless, fake greetd
    bash tests/integration/session_run.sh OUT_DIR                  # the session scripts, headless
    bash tests/container/run.sh OUT_DIR [e2e|migrate]              # real greetd and PAM in a container

The headless tests start a private Wayfire with the headless backend and a dead audio server, and drive it with
the `stipc` test plugin. Nothing reaches the running desktop. The container test needs a systemd-nspawn image
with greetd, Wayfire and Quickshell (`BASE`, default `exp-greetd-base`).

## License

GPL-3.0-or-later.
