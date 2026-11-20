import argparse
import json
import os
from pathlib import Path
import pwd
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import time

from gi.repository import Gio, GLib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from desktop_backend import plasma_layout, plasma_state, input_map
from native_display_kde_virtual import _Portal
from native_runtime_state import write_private


def events(path):
    return [json.loads(line.removeprefix('UURB_NATIVE_INPUT '))
            for line in path.read_text().splitlines() if line.startswith('UURB_NATIVE_INPUT ')]


def bridge_identity(path):
    subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'uu-native-bridge.service'], check=True)
    pid = subprocess.check_output(['systemctl', '--user', 'show', 'uu-native-bridge.service',
                                   '--property=MainPID', '--value'], text=True)
    return int(pid), json.loads(path.read_text())


def wait_event(path, predicate, process):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Input worker exited: %s' % path.read_text())
        for event in events(path):
            if predicate(event):
                return event
        time.sleep(0.05)
    raise RuntimeError('Input worker did not acknowledge the live map: %s' % path.read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--input-binary', type=Path, required=True)
    arguments = parser.parse_args()
    active_runtime = Path.home() / '.local/state/uurb/active-runtime.json'
    runtime_before = bridge_identity(active_runtime)
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(dir=root / 'build/kde-validation', prefix='input-map-') as temporary:
        directory = Path(temporary)
        token = secrets.token_hex(32)
        token_path = directory / 'token'
        token_path.write_text(token)
        token_path.chmod(0o600)
        baseline = plasma_layout(plasma_state())['monitors']
        mapping = directory / 'input-map.json'
        write_private(mapping, dict(version=1, map=input_map(baseline)))
        log_path = directory / 'input.log'
        with log_path.open('w') as log:
            worker = subprocess.Popen([str(arguments.input_binary.resolve()), '--user', pwd.getpwuid(os.getuid()).pw_name,
                '--token-file', str(token_path), '--seconds', '30', '--single-output',
                '--output-map-file', str(mapping)], stdout=log, stderr=log)
        portal = _Portal(Gio.bus_get_sync(Gio.BusType.SESSION, None), Gio, GLib)
        screen = None
        try:
            ready = wait_event(log_path, lambda event: event.get('event') == 'ready', worker)
            with socket.create_connection(('127.0.0.1', ready['port']), timeout=3) as client:
                client.sendall(struct.pack('<II64s', 0x58315255, 3, token.encode()))
                response = bytearray()
                while len(response) < 16:
                    part = client.recv(16 - len(response))
                    if not part:
                        raise RuntimeError('Input handshake closed')
                    response.extend(part)
                if struct.unpack('<4I', response) != (0x58315255, 0, 1, 0):
                    raise RuntimeError('Input authentication failed')
                screen = portal.open(arguments.state)
                monitors = plasma_layout(plasma_state())['monitors']
                if len(monitors) != len(baseline) + 1:
                    raise RuntimeError('The real virtual output did not appear')
                write_private(mapping, dict(version=1, map=input_map(monitors)))
                wait_event(log_path, lambda event: event.get('event') == 'output_map_updated' and
                           event.get('mapped_outputs') == len(monitors), worker)
                time.sleep(4)
                if bridge_identity(active_runtime) != runtime_before:
                    raise RuntimeError('The bridge restarted after adding a virtual output')
                portal.close(screen['session'])
                screen = None
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    restored = plasma_layout(plasma_state())['monitors']
                    if len(restored) == len(baseline):
                        break
                    time.sleep(0.1)
                if input_map(restored) != input_map(baseline):
                    raise RuntimeError('Physical input mapping did not restore')
                write_private(mapping, dict(version=1, map=input_map(restored)))
                count_before = len(events(log_path))
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and len(events(log_path)) == count_before:
                    if worker.poll() is not None:
                        raise RuntimeError('Input worker exited during restoration')
                    time.sleep(0.05)
                if events(log_path)[-1].get('mapped_outputs') != len(baseline):
                    raise RuntimeError('Input worker did not acknowledge restoration')
                time.sleep(4)
                if bridge_identity(active_runtime) != runtime_before:
                    raise RuntimeError('The bridge restarted after removing a virtual output')
                print(json.dumps(dict(event='live_input_map_verified', input_pid=worker.pid,
                                      mapped_outputs=[len(baseline), len(monitors), len(restored)],
                                      input_events_sent=0)), flush=True)
        finally:
            if screen is not None:
                portal.close(screen['session'])
            worker.terminate()
            worker.wait(timeout=5)
