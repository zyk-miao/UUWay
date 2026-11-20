import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

from gi.repository import Gio, GLib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from native_display_kde_virtual import _Portal


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--capture-binary', type=Path, required=True)
    arguments = parser.parse_args()
    portal = _Portal(Gio.bus_get_sync(Gio.BusType.SESSION, None), Gio, GLib)
    screen = portal.open(arguments.state)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as remote:
            remote.connect(str(Path(os.environ['XDG_RUNTIME_DIR']) / 'pipewire-0'))
            environment = dict(os.environ, UURB_CAPTURE_DURATION_SECONDS='2',
                               UURB_CAPTURE_SIZE='%dx%d' % (screen['width'], screen['height']))
            captured = subprocess.run([str(arguments.capture_binary), str(remote.fileno()),
                                       str(screen['node']), '--vulkan-import'],
                                      env=environment, pass_fds=(remote.fileno(),), timeout=15,
                                      capture_output=True, text=True)
            if captured.returncode:
                raise RuntimeError('Native capture failed: %s' % captured.stderr)
        metrics = json.loads(captured.stdout)
        if metrics['frames'] < 1 or metrics.get('dmabuf_only') is not True:
            raise RuntimeError('Virtual capture did not deliver valid DMA-BUF frames: %s' % metrics)
        if metrics['vulkan_imported_frames'] != metrics['frames']:
            raise RuntimeError('Virtual capture did not import every frame into Vulkan')
        if (metrics['width'], metrics['height']) != (screen['width'], screen['height']):
            raise RuntimeError('Virtual capture size differs from the portal output')
        print(json.dumps(dict(event='kde_virtual_capture_verified', **metrics)), flush=True)
    finally:
        portal.close(screen['session'])
