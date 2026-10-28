import argparse
import json
from pathlib import Path

from gi.repository import Gio, GLib

from desktop_backend import plasma_wayland
from native_display_kde_virtual import _Portal


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Authorize a KDE virtual display before a remote session')
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--width', type=int, required=True)
    parser.add_argument('--height', type=int, required=True)
    arguments = parser.parse_args()
    if not plasma_wayland():
        parser.error('Run authorization in the Plasma Wayland session')
    if any(not 320 <= value <= 4096 or value % 2 for value in (arguments.width, arguments.height)):
        parser.error('Virtual screen dimensions must be even and between 320 and 4096')
    arguments.state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    portal = _Portal(Gio.bus_get_sync(Gio.BusType.SESSION, None), Gio, GLib)
    screen = portal.open(arguments.state, interactive=True,
                         expected_size=(arguments.width, arguments.height))
    try:
        if not arguments.state.is_file():
            raise RuntimeError('KDE did not save authorization; enable remembered authorization')
        print(json.dumps(dict(event='kde_virtual_authorized', width=screen['width'],
                              height=screen['height'])), flush=True)
    finally:
        portal.close(screen['session'])
