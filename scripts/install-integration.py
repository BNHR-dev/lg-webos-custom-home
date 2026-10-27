#!/usr/bin/env python3
"""Install integration code disabled. SSH config/identity stay on the PC."""
import argparse
import io
import pathlib
import subprocess
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('--ssh-config', required=True)
parser.add_argument('--host', required=True, help='Alias in your private SSH config')
parser.add_argument('--update', action='store_true', help='Back up and replace only project code; leave daemon stopped')
parser.add_argument('--input-name', required=True, help='Measured device name, not event index')
parser.add_argument('--key-code', required=True, type=int, help='Measured Home key code')
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parents[1]
ssh = ['ssh', '-F', args.ssh_config, args.host]
archive = io.BytesIO()
with tarfile.open(fileobj=archive, mode='w:gz') as tar:
    for name in ['engine.py', 'control.py', 'probe.py']:
        tar.add(root/'system_integration'/name, arcname=name)
remote = '/var/lib/bnhr-customhome-integration'
if args.update:
    command = ('test "$(id -u)" = 0 && test -f ' + remote + '/config.json && '
               'python3 ' + remote + '/control.py stop && '
               'tar -czf ' + remote + '/code-before-update.tar.gz -C ' + remote +
               ' engine.py control.py config.json && tar -xzf - -C ' + remote)
else:
    command = 'test "$(id -u)" = 0 && test ! -e ' + remote + ' && mkdir -m 755 ' + remote + ' && tar -xzf - -C ' + remote
subprocess.run(ssh + [command], input=archive.getvalue(), check=True)
# shlex quotes only public configuration; credentials are never loaded by this script.
import shlex
command = 'python3 ' + remote + '/control.py init --input-name ' + shlex.quote(args.input_name) + ' --key-code ' + str(args.key_code)
if not args.update:
    subprocess.run(ssh + [command], check=True)
print('Code installed; daemon stopped. Initial installs are disabled and have no boot hook.')
