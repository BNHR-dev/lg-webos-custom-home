#!/usr/bin/python3
"""Passive Home integration and bounded boot/wake handling. No firmware edits."""
import collections
import fcntl
import json
import os
import pathlib
import selectors
import signal
import struct
import subprocess
import time

INPUT_FORMAT = '@llHHi'
INPUT_SIZE = struct.calcsize(INPUT_FORMAT)


def read_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.new')
    temp.write_text(json.dumps(value, sort_keys=True) + '\n')
    temp.replace(path)


def luna(method, payload, timeout=3):
    # stdin must remain open until Luna exits; communicate()/DEVNULL closes it too early.
    p = subprocess.Popen(['luna-send', '-w', str(int(timeout * 1000)), '-n', '1', method,
                          json.dumps(payload)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    try:
        p.wait(timeout=timeout + 1)
        data = p.stdout.read()
        return json.loads(data) if data else {'returnValue': False, 'errorText': 'empty response'}
    except (subprocess.TimeoutExpired, ValueError):
        return {'returnValue': False, 'errorText': 'timeout or invalid response'}
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=1)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
        p.stdin.close(); p.stdout.close()


class JSONStream:
    def __init__(self):
        self.text = ''
        self.decoder = json.JSONDecoder()

    def feed(self, data):
        self.text += data.decode('utf-8', errors='replace')
        result = []
        while self.text.strip():
            self.text = self.text.lstrip()
            try:
                item, end = self.decoder.raw_decode(self.text)
            except ValueError:
                break
            result.append(item)
            self.text = self.text[end:]
        if len(self.text) > 65536:
            self.text = ''
            raise ValueError('oversized service response')
        return result


class ShortHome:
    def __init__(self, code, max_hold=.65):
        self.code, self.max_hold = code, max_hold
        self.down = {}

    def event(self, device, code, value, event_time):
        if code != self.code:
            return False
        if value == 1:
            self.down.setdefault(device, event_time)
        elif value == 0:
            start = self.down.pop(device, None)
            return start is not None and 0 <= event_time - start < self.max_hold
        return False


class PowerTransitions:
    OFF = {'suspend', 'activestandby', 'standby', 'poweroff'}

    def __init__(self):
        self.previous = None

    def event(self, state):
        current = str(state).lower().replace(' ', '')
        wake = self.previous in self.OFF and current == 'active'
        self.previous = current
        return wake


def boot_time():
    for line in pathlib.Path('/proc/stat').read_text().splitlines():
        if line.startswith('btime '):
            return line.split()[1]
    raise RuntimeError('kernel boot time unavailable')


class Daemon:
    def __init__(self, root, runtime, boot=False):
        self.root, self.runtime = pathlib.Path(root), pathlib.Path(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / 'config.json'
        self.running = True
        self.select = selectors.DefaultSelector()
        self.inputs = {}
        self.input_buffers = {}
        self.power_child = None
        self.power_parser = JSONStream()
        self.power_state = PowerTransitions()
        self.next_input_scan = 0
        self.next_subscribe = 0
        self.subscribe_backoff = 1
        self.pending_home = None
        self.pending_power = None
        self.last_launch = -100
        self.counts = collections.Counter()
        self.last_errors = {}
        self.started = time.time()
        self.boot_requested = boot
        self.boot_deadline = time.monotonic() + 90
        self.config = {}
        self.home_keys = None
        self.stopping = False

    def log(self, event, **detail):
        path = self.runtime / 'events.jsonl'
        if path.exists() and path.stat().st_size > 65536:
            path.replace(self.runtime / 'events.previous.jsonl')
        with path.open('a') as f:
            f.write(json.dumps({'time': time.time(), 'event': event, **detail}) + '\n')
        self.counts[event] += 1

    def error(self, event, **detail):
        now = time.monotonic()
        if now - self.last_errors.get(event, -100) >= 30:
            self.log(event, **detail)
            self.last_errors[event] = now

    def close_inputs(self):
        for fd in list(self.inputs):
            self.select.unregister(fd); os.close(fd)
        self.inputs.clear(); self.input_buffers.clear()
        self.pending_home = None

    def scan_inputs(self):
        if self.inputs:
            return
        for file in pathlib.Path('/sys/class/input').glob('event*/device/name'):
            if file.read_text().strip() != self.config['input_name']:
                continue
            device = '/dev/input/' + file.parts[-3]
            fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
            # Read device identity only. Never EVIOCGRAB or write to an input device.
            buf = bytearray(256)
            fcntl.ioctl(fd, 0x81004506, buf, True)
            name = bytes(buf).split(b'\0')[0].decode(errors='replace')
            if name != self.config['input_name']:
                os.close(fd); continue
            self.inputs[fd] = device; self.input_buffers[fd] = b''
            self.select.register(fd, selectors.EVENT_READ, 'input')
            self.log('input_open', name=name, event_size=INPUT_SIZE)
        if not self.inputs:
            self.error('input_unavailable')

    def stop_power(self):
        if self.power_child is not None:
            p = self.power_child
            self.select.unregister(p.stdout)
            p.terminate()
            try:
                p.wait(timeout=1)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
            p.stdin.close(); p.stdout.close()
            self.power_child = None

    def start_power(self):
        p = subprocess.Popen(['luna-send', '-i',
                              'luna://com.webos.service.tvpower/power/getPowerState',
                              '{"subscribe":true}'], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        os.set_blocking(p.stdout.fileno(), False)
        self.power_child = p; self.power_parser = JSONStream()
        self.select.register(p.stdout, selectors.EVENT_READ, 'power')

    def refresh(self):
        old = self.config
        self.config = read_json(self.config_path, {})
        if self.config.get('lease_until', 0) and time.time() >= self.config['lease_until']:
            self.config['home'] = False; self.config['lease_until'] = 0
            write_json(self.config_path, self.config)
            self.log('temporary_home_expired')
        if not self.config.get('home'):
            self.pending_home = None
            if self.inputs: self.close_inputs()
        elif not old.get('home') or old.get('home_key_code') != self.config.get('home_key_code'):
            if self.inputs: self.close_inputs()
            self.home_keys = ShortHome(self.config['home_key_code'], self.config.get('max_hold', .65))
        if not self.config.get('power'):
            self.stop_power(); self.pending_power = None
        elif not old.get('power'):
            self.power_state = PowerTransitions()  # A fresh Active snapshot must not steal focus.
        if self.boot_requested:
            self.boot_requested = False
            marker = self.runtime / 'boot-handled.json'
            if not marker.exists():
                write_json(marker, {'handled': True})
                uptime = float(pathlib.Path('/proc/uptime').read_text().split()[0])
                if self.config.get('power') and uptime < 180:
                    self.pending_power = {'reason': 'boot', 'due': time.monotonic(), 'tries': 0}
                    self.log('boot_pending')

    def read_input(self, fd):
        try:
            data = os.read(fd, INPUT_SIZE * 64)
            if not data: raise OSError('input closed')
            data = self.input_buffers[fd] + data
            count = len(data) // INPUT_SIZE
            self.input_buffers[fd] = data[count * INPUT_SIZE:]
            for i in range(count):
                sec, usec, typ, code, value = struct.unpack(INPUT_FORMAT, data[i * INPUT_SIZE:(i + 1) * INPUT_SIZE])
                if typ != 1: continue
                if not (0 <= usec < 1000000 and abs(sec - time.time()) < 10):
                    self.error('input_timestamp_invalid'); continue
                if self.home_keys.event(fd, code, value, sec + usec / 1000000):
                    now = time.monotonic()
                    self.pending_home = {'due': max(now + .3, self.last_launch + .8), 'until': now + 2, 'tries': 0}
                    self.log('home_short')
        except OSError:
            self.select.unregister(fd); os.close(fd)
            del self.inputs[fd]; del self.input_buffers[fd]
            self.home_keys.down.pop(fd, None)
            self.error('input_disconnected')

    def read_power(self):
        data = os.read(self.power_child.stdout.fileno(), 16384)
        if not data:
            self.stop_power(); self.next_subscribe = time.monotonic() + self.subscribe_backoff
            self.subscribe_backoff = min(30, self.subscribe_backoff * 2)
            self.error('power_subscription_closed'); return
        for msg in self.power_parser.feed(data):
            if not msg.get('returnValue', True):
                self.error('power_subscription_rejected'); self.stop_power()
                self.next_subscribe = time.monotonic() + 30; return
            state = msg.get('state')
            if not state: continue
            self.subscribe_backoff = 1
            if self.power_state.event(state):
                self.pending_power = {'reason': 'wake', 'due': time.monotonic() + .7, 'until': time.monotonic() + 15, 'tries': 0}
                self.log('wake_pending')
            self.log('power_state', state=state)

    def launch(self, reason):
        if time.monotonic() - self.last_launch < .8:
            self.log('launch_coalesced', reason=reason); return True
        result = luna('luna://com.webos.applicationManager/launch', {'id': self.config['app_id']})
        if result.get('returnValue'):
            self.last_launch = time.monotonic(); self.log('launch', reason=reason)
            return True
        self.error('launch_failed', reason=reason, error=result.get('errorText', 'unknown'))
        return False

    def actions(self):
        now = time.monotonic()
        if self.pending_home and now >= self.pending_home['due']:
            job = self.pending_home
            foreground = luna('luna://com.webos.applicationManager/getForegroundAppInfo', {})
            now = time.monotonic()
            if foreground.get('appId') == self.config['stock_home'] and now <= job['until']:
                self.pending_home = None
                if self.launch('home'): self.pending_power = None
            elif now >= job['until'] or job['tries'] >= 4:
                self.log('home_no_redirect'); self.pending_home = None
            else:
                job['tries'] += 1; job['due'] = now + .25
        if self.pending_power and now >= self.pending_power['due']:
            job = self.pending_power
            if job.get('until') and now > job['until']:
                self.log('wake_wait_expired'); self.pending_power = None; return
            if time.monotonic() > self.boot_deadline and job['reason'] == 'boot':
                self.log('boot_wait_expired'); self.pending_power = None; return
            if self.power_state.previous != 'active':
                job['due'] = now + 1; return
            foreground = luna('luna://com.webos.applicationManager/getForegroundAppInfo', {})
            current = foreground.get('appId')
            if job.get('baseline') and current and current != job['baseline'] and current not in [self.config['stock_home'], self.config['app_id']]:
                self.log('power_user_navigation_cancelled'); self.pending_power = None; return
            if current and 'baseline' not in job: job['baseline'] = current
            if current == self.config['app_id'] or self.launch(job['reason']):
                self.pending_power = None
            else:
                job['tries'] += 1
                if job['tries'] >= 8:
                    self.log('power_retries_exhausted'); self.pending_power = None
                else: job['due'] = now + 2

    def run(self):
        self.lock = (self.runtime / 'daemon.lock').open('a')
        try: fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: return 0
        (self.runtime / 'daemon.pid').write_text(str(os.getpid()))
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, 'running', False))
        signal.signal(signal.SIGINT, lambda *_: setattr(self, 'running', False))
        self.log('daemon_started', boot=self.boot_requested)
        try:
            while self.running:
                self.refresh(); now = time.monotonic()
                if self.config.get('home') and now >= self.next_input_scan:
                    self.scan_inputs(); self.next_input_scan = now + 5
                if self.config.get('power') and self.power_child is None and now >= self.next_subscribe:
                    self.start_power()
                for item, _ in self.select.select(.15):
                    if item.data == 'input': self.read_input(item.fd)
                    else: self.read_power()
                self.actions()
                write_json(self.runtime / 'status.json', {'pid': os.getpid(), 'started': self.started,
                           'counts': dict(self.counts), 'input_devices': list(self.inputs.values()),
                           'power_child': self.power_child.pid if self.power_child else None,
                           'power_state': self.power_state.previous, 'home_enabled': bool(self.config.get('home')),
                           'power_enabled': bool(self.config.get('power'))})
        finally:
            self.close_inputs(); self.stop_power(); self.select.close()
            (self.runtime / 'daemon.pid').unlink(missing_ok=True)
            self.log('daemon_stopped')
            self.lock.close()
        return 0
