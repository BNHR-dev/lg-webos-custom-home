#!/usr/bin/python3
"""Management of only this project's integration. Does not alter root/SSH hooks."""
import argparse
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time
from engine import Daemon, boot_time, luna, read_json, write_json

ROOT = pathlib.Path('/var/lib/bnhr-customhome-integration')
RUNTIME = pathlib.Path('/tmp/bnhr-customhome-integration')
HOOK = pathlib.Path('/var/lib/webosbrew/init.d/40-bnhr-customhome-integration')


def pid():
    try:
        value = int((RUNTIME / 'daemon.pid').read_text())
        args = pathlib.Path('/proc', str(value), 'cmdline').read_bytes().split(b'\0')
        if str(ROOT / 'control.py').encode() not in args or b'run' not in args:
            return None
        os.kill(value, 0)
        return value
    except (OSError, ValueError):
        return None


def start(boot=False):
    if pid():
        return
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / 'process.log').open('ab') as out:
        subprocess.Popen([sys.executable, str(ROOT / 'control.py'), 'run'] + (['--boot'] if boot else []),
                         stdin=subprocess.DEVNULL, stdout=out, stderr=out, start_new_session=True,
                         close_fds=True)
    for _ in range(20):
        if pid(): return
        time.sleep(.1)
    raise RuntimeError('Daemon did not start; inspect its bounded local log')


def stop():
    value = pid()
    if value is None: return
    os.kill(value, signal.SIGTERM)
    for _ in range(80):
        if pid() is None: return
        time.sleep(.1)
    # Only the identified project process, never another service or SSH process.
    if os.getpgid(value) == value: os.killpg(value, signal.SIGKILL)
    else: os.kill(value, signal.SIGKILL)
    raise RuntimeError('Daemon needed SIGKILL; inspect children before restarting')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['init', 'status', 'home', 'power', 'start', 'stop',
                                           'persist', 'lg-home', 'remove', 'run'])
    parser.add_argument('value', nargs='?')
    parser.add_argument('--input-name')
    parser.add_argument('--key-code', type=int)
    parser.add_argument('--app-id', default='com.bnhr.customhome')
    parser.add_argument('--temporary', type=int, default=0)
    parser.add_argument('--boot', action='store_true')
    args = parser.parse_args()
    if os.getuid() != 0: raise RuntimeError('Administrator access required')
    path = ROOT / 'config.json'
    config = read_json(path, {})
    if args.command == 'init':
        if config: raise RuntimeError('Configuration already exists; not replaced')
        if not args.input_name or args.key_code is None:
            raise RuntimeError('Measured input name and key code required')
        config = {'app_id': args.app_id, 'stock_home': 'com.webos.app.home',
                  'input_name': args.input_name, 'home_key_code': args.key_code,
                  'max_hold': .65, 'home': False, 'power': False, 'lease_until': 0}
        write_json(path, config)
        write_json(RUNTIME / 'boot-handled.json', {'handled': True})
    elif args.command == 'status':
        state = read_json(RUNTIME / 'status.json', {})
        print(json.dumps({'config': config, 'daemon_pid': pid(), 'persistent_hook': HOOK.exists(),
                          'runtime': state}, indent=2)); return
    elif args.command == 'run':
        if not config: raise RuntimeError('Not initialized')
        return Daemon(ROOT, RUNTIME, args.boot).run()
    elif args.command == 'stop': stop(); return
    elif args.command == 'start': start(args.boot); return
    elif args.command in ['home', 'power']:
        if args.value not in ['on', 'off']: raise RuntimeError('Use on or off')
        config[args.command] = args.value == 'on'
        if args.command == 'home':
            config['lease_until'] = time.time() + args.temporary if config['home'] and args.temporary else 0
        if args.command == 'power' and config['power']:
            # Enabling midway through a session must not create a fake boot.
            write_json(RUNTIME / 'boot-handled.json', {'handled': True})
        write_json(path, config)
        if config['home'] or config['power']: start()
    elif args.command == 'persist':
        if args.value == 'on':
            config['lease_until'] = 0; write_json(path, config)
            HOOK.parent.mkdir(parents=True, exist_ok=True)
            HOOK.write_text('#!/bin/sh\n# Only BNHR integration; root/SSH startup is separate.\n'
                            'test -f /var/lib/bnhr-customhome-integration/control.py || exit 0\n'
                            'exec /usr/bin/python3 /var/lib/bnhr-customhome-integration/control.py start --boot\n')
            HOOK.chmod(0o755)
        elif args.value == 'off': HOOK.unlink(missing_ok=True)
        else: raise RuntimeError('Use on or off')
    elif args.command == 'lg-home':
        # No redirection occurs without a short physical Home press.
        result = luna('luna://com.webos.applicationManager/launch', {'id': config['stock_home']})
        print(json.dumps(result)); return
    elif args.command == 'remove':
        stop(); HOOK.unlink(missing_ok=True)
        # Fixed project directories only. Never remove applications, webosbrew or root hooks.
        shutil.rmtree(ROOT)
        shutil.rmtree(RUNTIME, ignore_errors=True)
        print('Only BNHR system integration removed; launcher and root/SSH kept.'); return
    print(json.dumps({'home': config.get('home'), 'power': config.get('power'), 'daemon_pid': pid(),
                      'persistent_hook': HOOK.exists()}))


if __name__ == '__main__':
    try:
        sys.exit(main() or 0)
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
