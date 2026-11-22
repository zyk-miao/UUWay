import hashlib
import json
import os
from pathlib import Path
import time

import pulsectl


class DesktopAudioBridge:
    def __init__(self, prefix, source_sink=None):
        identity = hashlib.sha256(os.fsencode(Path(prefix).resolve())).hexdigest()[:16]
        self.sink_name = 'uuway_audio_' + identity
        self.source_sink = source_sink
        self.null_arguments = (
            f'sink_name={self.sink_name} format=s16le rate=48000 channels=2 '
            'channel_map=front-left,front-right '
            f'sink_properties="device.description={self.sink_name} '
            'device.class=abstract priority.session=0 priority.driver=0"')
        self.loopback_suffix = (
            f' sink={self.sink_name} source_dont_move=true sink_dont_move=true '
            'latency_msec=20 rate=48000 channels=2 channel_map=front-left,front-right '
            'sink_input_properties="application.id=org.uuway.desktop-audio"')
        self.modules = []
        self.loopback = None
        self.monitor = None
        self.route = None
        self.next_poll = 0
        self.pulse = None

    def failure(self, reason, message):
        print(json.dumps(dict(event='native_audio_failed', reason=reason)), flush=True)
        raise RuntimeError(message)

    def source_ready(self, monitor, route):
        changed = monitor != self.monitor or route != self.route
        self.monitor = monitor
        self.route = route
        if changed:
            print(json.dumps(dict(event='native_audio_source_ready', monitor=monitor,
                                  sink=self.sink_name, route=route, rate=48000, channels=2)), flush=True)

    def listing(self):
        return [dict(index=module.index, name=module.name, argument=module.argument)
                for module in self.pulse.module_list()]

    def owned(self, module):
        return ((module['name'] == 'module-null-sink' and
                 module['argument'] == self.null_arguments) or
                (module['name'] == 'module-loopback' and
                 module['argument'].endswith(self.loopback_suffix)))

    def unload(self, module):
        current = next((item for item in self.listing()
                        if item.get('index') == module['index']), None)
        if current is None:
            return
        if any(current.get(key) != module.get(key) for key in ('index', 'name', 'argument')):
            self.failure('module_identity_changed', 'Desktop audio module identity changed')
        self.pulse.module_unload(module['index'])

    def load(self, name, arguments):
        index = self.pulse.module_load(name, arguments)
        module = next(item for item in self.listing() if item.get('index') == index)
        if not self.owned(module):
            self.failure('unexpected_module', 'Unexpected desktop audio module')
        self.modules.append(module)
        return module

    def start(self):
        self.pulse = pulsectl.Pulse('uuway-desktop-audio')
        # 固定名称仅属于这个 Wine prefix，重启时清理相同配置的遗留资源。
        stale = [item for item in self.listing() if self.owned(item)]
        for module in sorted(stale, key=lambda item: item['name'] == 'module-null-sink'):
            self.unload(module)
        self.load('module-null-sink', self.null_arguments)
        sink = self.pulse.get_sink_by_name(self.sink_name)
        self.pulse.mute(sink, False)
        self.pulse.volume_set_all_chans(sink, 1.0)
        self.poll(force=True)

    def poll(self, force=False):
        if not force and time.monotonic() < self.next_poll:
            return
        self.next_poll = time.monotonic() + 1
        modules = self.listing()
        if any(not any(all(current.get(key) == module.get(key)
                           for key in ('index', 'name', 'argument'))
                       for current in modules)
               for module in self.modules if module != self.loopback):
            self.failure('owned_module_missing', 'Desktop audio module disappeared')
        name = self.source_sink or self.pulse.server_info().default_sink_name
        sink = next((item for item in self.pulse.sink_list() if item.name == name), None)
        if sink is None:
            self.failure('source_unavailable', 'Desktop audio output device is unavailable')
        monitor = sink.monitor_source_name
        if not monitor or any(character.isspace() or character in '\\"\'' for character in monitor):
            raise ValueError('Invalid desktop audio monitor name')
        # 默认输出指向专用设备时，应用直接向其中播放；此时无需创建回环。
        if name == self.sink_name:
            if self.loopback is not None:
                self.unload(self.loopback)
                self.modules.remove(self.loopback)
                self.loopback = None
            self.source_ready(monitor, 'direct')
            return
        if monitor == self.monitor:
            if self.loopback not in modules:
                self.failure('loopback_missing', 'Desktop audio module disappeared')
            return
        if self.loopback is not None:
            self.unload(self.loopback)
            self.modules.remove(self.loopback)
            self.loopback = None
        self.loopback = self.load('module-loopback', f'source={monitor}' + self.loopback_suffix)
        self.source_ready(monitor, 'monitor')

    def stop(self):
        if self.pulse is None:
            return
        try:
            for module in reversed(self.modules):
                self.unload(module)
            self.modules.clear()
            self.loopback = None
            self.monitor = None
            self.route = None
        finally:
            self.pulse.close()
            self.pulse = None
