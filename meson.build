project('mavernix-greeter', version: '0.1.4', license: 'GPL-3.0-or-later', meson_version: '>=1.3.0')

libdir = get_option('prefix') / get_option('libexecdir') / 'mavernix-greeter'
datadir = get_option('prefix') / get_option('datadir') / 'mavernix-greeter'
pydir = libdir / 'python'

install_data(
    'src/session/greeter-session', 'src/session/run-greeter', 'src/session/text-greeter',
    'src/session/x11-session', 'src/session/session-wrap', 'tools/migrate',
    install_dir: libdir, install_mode: 'rwxr-xr-x')
configure_file(input: 'src/helper/launcher.in', output: 'helper', configuration: {'PYDIR': pydir, 'MODULE': 'cli'},
    install_dir: libdir, install_mode: 'rwxr-xr-x')
configure_file(input: 'src/helper/launcher.in', output: 'mavernix-greeter-sync',
    configuration: {'PYDIR': pydir, 'MODULE': 'sync_cli'},
    install_dir: get_option('prefix') / get_option('bindir'), install_mode: 'rwxr-xr-x')
install_subdir('src/helper/mavernix_greeter', install_dir: pydir, exclude_directories: ['__pycache__'])
install_subdir('src/greeter', install_dir: datadir)
install_subdir('data/themes', install_dir: datadir)
install_data('data/greeter.toml', 'data/greetd-config.toml', install_dir: datadir)
install_data('data/mavernix-greeter-sync@.path', 'data/mavernix-greeter-sync@.service',
    install_dir: get_option('prefix') / 'lib/systemd/system')
install_data('data/tmpfiles.conf', rename: 'mavernix-greeter.conf',
    install_dir: get_option('prefix') / 'lib/tmpfiles.d')

python = find_program('python3')
node = find_program('node', required: false)
test('python', python, args: ['-m', 'unittest', 'discover', '-s', meson.project_source_root() / 'tests'],
    env: {'PYTHONPATH': meson.project_source_root() / 'src/helper'}, workdir: meson.project_source_root())
if node.found()
    test('js', node, args: ['--test', meson.project_source_root() / 'tests'], workdir: meson.project_source_root())
endif
