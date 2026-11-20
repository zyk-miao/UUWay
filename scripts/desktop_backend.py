"""Desktop-specific, read-only topology for the native input/capture worker."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess


def _packaged_wine_directory():
    """The AUR package ships its own hash-verified WineHQ 11.0 here.

    Kept as a seam so tests do not depend on whether this host has uuway-git
    installed.
    """
    return Path('/opt/uuway/wine-11.0/bin')


def wine_bin_directory(system=Path('/opt/wine-stable/bin'), local=None):
    local = local if local is not None else Path.home() / '.local/opt/uuway/wine-11.0/bin'
    packaged = _packaged_wine_directory()
    if (packaged / 'wine').is_file():
        return packaged
    return local if not (system / 'wine').is_file() and (local / 'wine').is_file() else system


def plasma_wayland(environ=None):
    environ = os.environ if environ is None else environ
    return (environ.get('XDG_SESSION_TYPE') == 'wayland' and
            'KDE' in environ.get('XDG_CURRENT_DESKTOP', '').split(':'))


# The Windows display ABI enumerates at most eight outputs and validates each
# one's current mode against these bounds (src/native_display_api.h).
MAX_WINDOWS_OUTPUTS = 8
MAX_OUTPUT_PIXELS = 4096
MAX_WINDOWS_REFRESH_HZ = 144
# Absolute uinput axes and SendInput both span 0..65535; KWin maps the uinput
# range over the bounding box of every enabled output in logical pixels.
ABSOLUTE_AXIS_MAX = 65535
# Windows monitors are laid out at physical size, which can exceed their
# logical extent by KScreen's rounding of fractional logical widths. Spread
# positions slightly further so neighbouring rectangles never overlap.
WINDOWS_LAYOUT_MARGIN = 1.001
# KScreen rotation flags: 1 none, 2 left, 4 inverted, 8 right.
KSCREEN_ROTATION_NONE = 1
KSCREEN_QUARTER_TURNS = (2, 8)


def _even_size(size):
    return isinstance(size, dict) and all(
        type(size.get(key)) is int and 2 <= size[key] <= MAX_OUTPUT_PIXELS and size[key] % 2 == 0
        for key in ('width', 'height'))


def _output_active(output):
    """Whether KWin is currently driving this output.

    KWin omits ``enabled`` for portal-owned virtual outputs: they exist exactly
    while their ScreenCast session lives, so their presence is the state.
    """
    return output.get('enabled') is True or str(output.get('name', '')).startswith('Virtual-')


def _plasma_output(output):
    """Validated geometry of one enabled output, or None when Windows cannot show it."""
    name, position, size, scale = output.get('name'), output.get('pos'), output.get('size'), output.get('scale')
    if (output.get('connected') is not True or not isinstance(name, str) or not 0 < len(name) <= 128 or
            not isinstance(position, dict) or any(type(position.get(axis)) is not int or
                                                  not -32768 <= position[axis] <= 32767 for axis in ('x', 'y')) or
            type(scale) not in (int, float) or not math.isfinite(scale) or not 0.5 <= scale <= 4):
        raise RuntimeError('Invalid KDE output geometry')
    rotation = output.get('rotation')
    turned = rotation in KSCREEN_QUARTER_TURNS
    if not isinstance(size, dict) or any(type(size.get(key)) is not int or size[key] < 1 for key in ('width', 'height')):
        raise RuntimeError('Invalid KDE output size')
    logical = dict(x=position['x'], y=position['y'],
                   width=(size['height'] if turned else size['width']) / scale,
                   height=(size['width'] if turned else size['height']) / scale)
    modes = output.get('modes')
    current = [mode for mode in modes if isinstance(mode, dict) and mode.get('id') == output.get('currentModeId')] \
        if isinstance(modes, list) and 1 <= len(modes) <= 256 else []
    refresh = current[0].get('refreshRate') if len(current) == 1 else None
    shown = (rotation == KSCREEN_ROTATION_NONE and output.get('replicationSource', 0) == 0 and _even_size(size) and
             len(current) == 1 and current[0].get('size') == size and
             type(refresh) in (int, float) and math.isfinite(refresh) and refresh >= 1)
    return dict(name=name, logical=logical, primary=output.get('priority') == 1, shown=shown,
                virtual=name.startswith('Virtual-'),
                width=size['width'], height=size['height'], scale=float(scale), mode=output.get('currentModeId'),
                refresh=round(min(float(refresh), float(MAX_WINDOWS_REFRESH_HZ)), 3) if shown else None)


def plasma_layout(data):
    """Every enabled KScreen output, mapped into a Windows virtual desktop.

    Windows sees each output at its physical mode size, so UU's video frames
    and monitor rectangles agree. Positions are KWin's logical positions,
    relative to the primary output and stretched by the largest scale so that
    mixed-DPI neighbours never overlap. ``input`` keeps each shown output's
    logical rectangle in KWin's absolute-axis space for the input worker.
    Mirrored, rotated or odd-sized outputs stay in KWin's bounding box but are
    not offered to Windows.
    """
    outputs = data.get('outputs') if isinstance(data, dict) else None
    if not isinstance(outputs, list) or not 1 <= len(outputs) <= 16:
        raise RuntimeError('Invalid KDE output list')
    enabled = [_plasma_output(item) for item in outputs if isinstance(item, dict) and _output_active(item)]
    shown = [item for item in enabled if item['shown']]
    if not shown:
        raise RuntimeError('KDE 没有可串流的显示器；请保持至少一台显示器未镜像、未旋转')
    if len(shown) > MAX_WINDOWS_OUTPUTS:
        raise RuntimeError('KDE enables more outputs than the Windows display API supports')
    primary = next((item for item in shown if item['primary']), None) or \
        next((item for item in shown if not item['logical']['x'] and not item['logical']['y']), None) or \
        min(shown, key=lambda item: (item['logical']['y'], item['logical']['x'], item['name']))
    ordered = [primary] + sorted((item for item in shown if item is not primary),
                                 key=lambda item: (item['logical']['y'], item['logical']['x'], item['name']))
    stretch = max(item['scale'] for item in shown) * WINDOWS_LAYOUT_MARGIN
    left = min(item['logical']['x'] for item in enabled)
    top = min(item['logical']['y'] for item in enabled)
    right = max(item['logical']['x'] + item['logical']['width'] for item in enabled)
    bottom = max(item['logical']['y'] + item['logical']['height'] for item in enabled)

    def windows_offset(value, origin):
        # Round away from the primary origin: the spacing then never shrinks
        # below the stretched logical gap, which already exceeds each width.
        delta = (value - origin) * stretch
        return math.ceil(delta) if delta >= 0 else math.floor(delta)

    def axis(value, low, high):
        return round((value - low) / (high - low) * ABSOLUTE_AXIS_MAX)

    monitors = []
    for index, item in enumerate(ordered):
        logical = item['logical']
        x0, y0 = axis(logical['x'], left, right), axis(logical['y'], top, bottom)
        monitors.append(dict(
            index=index, connector=item['name'], gdi_name='\\\\.\\DISPLAY%d' % (index + 1),
            friendly=item['name'], virtual=item['virtual'], primary=index == 0, mode=item['mode'],
            x=windows_offset(logical['x'], primary['logical']['x']),
            y=windows_offset(logical['y'], primary['logical']['y']),
            width=item['width'], height=item['height'], refresh=item['refresh'], scale=item['scale'],
            device_path='\\\\?\\DISPLAY#UURB#%s#%d' % (item['name'], index),
            modes=[dict(width=item['width'], height=item['height'], refresh=item['refresh'], scales=[item['scale']])],
            input=dict(x=x0, y=y0, width=axis(logical['x'] + logical['width'], left, right) - x0,
                       height=axis(logical['y'] + logical['height'], top, bottom) - y0)))
    # KScreen does not expose Mutter's serial. A stable state fingerprint lets
    # the existing worker detect changes without reporting EDID or monitor IDs.
    state = [[item['name'], item['mode'], item['logical'], item['scale'], item['shown']] for item in enabled]
    serial = int.from_bytes(hashlib.sha256(json.dumps(state, sort_keys=True).encode()).digest()[:4], 'big')
    return dict(serial=serial, monitors=monitors)


def input_map(monitors):
    """``--output-map`` for uu-native-input: Windows rectangle to absolute-axis rectangle, primary first."""
    return ';'.join('%d,%d,%d,%d,%d,%d,%d,%d' % (
        item['x'], item['y'], item['width'], item['height'],
        item['input']['x'], item['input']['y'], item['input']['width'], item['input']['height'])
        for item in monitors)


def plasma_topology(data):
    """Worker topology: the primary output as the tracked origin, plus the whole input map.

    The map covers every shown output and is refreshed by the input worker
    while the remote session remains active.
    """
    layout = plasma_layout(data)
    primary = layout['monitors'][0]
    return dict(generation=layout['serial'], connectors=[primary['connector']],
                layout=[dict(x=0, y=0, scale=primary['scale'], transform=0, outputs=1)],
                modes=[dict(width=primary['width'], height=primary['height'])],
                input_map=input_map(layout['monitors']))


def output_restore_state(restore_state, connector):
    """Per-output portal restore file beside the legacy single-output one.

    KDE grants and restores screen sharing per screen, and a token is
    rotated on every use, so each output keeps its own.
    """
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', connector):
        raise ValueError('Unexpected KDE output name')
    path = Path(restore_state)
    return path.with_name('%s.%s%s' % (path.stem, connector, path.suffix))


def plasma_state():
    # Qt checks whether ALWAYS_ON is present, so even '0' forces AT-SPI on.
    # An explicit bus address also bypasses desktop policy. Remove both only
    # from this short-lived geometry helper, leaving the parent unchanged.
    environment = dict(os.environ, QT_ACCESSIBILITY='0', NO_AT_BRIDGE='1')
    environment.pop('QT_LINUX_ACCESSIBILITY_ALWAYS_ON', None)
    environment.pop('AT_SPI_BUS_ADDRESS', None)
    result = subprocess.run(['kscreen-doctor', '-j'], capture_output=True, text=True,
                            timeout=5, check=True, env=environment)
    return json.loads(result.stdout)


def current_plasma_topology():
    return plasma_topology(plasma_state())
