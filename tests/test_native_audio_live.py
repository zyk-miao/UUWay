import array
import importlib.util
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import pulsectl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from native_audio import DesktopAudioBridge
from desktop_backend import wine_bin_directory
from audio_session import fetch_component, install_component


@unittest.skipUnless(os.environ.get('UUWAY_LIVE_AUDIO_TESTS') == '1',
                     'Requires UUWAY_LIVE_AUDIO_TESTS=1, PulseAudio/PipeWire, Wine and MinGW')
class NativeAudioLiveTests(unittest.TestCase):
    def test_output_removal_reconnects_to_selected_source(self):
        bridge = DesktopAudioBridge(ROOT / 'build/audio-validation/source-removal')
        with pulsectl.Pulse('uuway-audio-removal-test') as pulse:
            modules = []
            try:
                names = ['uuway_audio_removal_a', 'uuway_audio_removal_b']
                for name in names:
                    modules.append(pulse.module_load('module-null-sink',
                        f'sink_name={name} sink_properties="priority.session=0 priority.driver=0"'))
                bridge.source_sink = names[0]
                bridge.start()
                pulse.module_unload(modules.pop(0))
                bridge.source_sink = names[1]
                bridge.poll(force=True)
                self.assertEqual(bridge.monitor, names[1] + '.monitor')
                self.assertEqual(sum(bridge.owned(module) for module in bridge.listing()), 2)
            finally:
                bridge.stop()
                for module in reversed(modules):
                    pulse.module_unload(module)

    def test_stale_modules_recovery_and_missing_module_failure(self):
        work = ROOT / 'build/audio-validation/recovery'
        pulse = pulsectl.Pulse('uuway-audio-recovery-test')
        source = pulse.module_load('module-null-sink',
            'sink_name=uuway_audio_recovery_source sink_properties="priority.session=0 priority.driver=0"')
        bridge = DesktopAudioBridge(work, 'uuway_audio_recovery_source')
        restarted = DesktopAudioBridge(work, 'uuway_audio_recovery_source')
        try:
            bridge.start()
            bridge.pulse.close()
            bridge.pulse = None
            restarted.start()
            self.assertEqual(sum(restarted.owned(module) for module in restarted.listing()), 2)
            restarted.pulse.module_unload(restarted.loopback['index'])
            with self.assertRaisesRegex(RuntimeError, 'module disappeared'):
                restarted.poll(force=True)
        finally:
            restarted.stop()
            bridge.stop()
            pulse.module_unload(source)
            pulse.close()

    def test_owned_output_captures_directly_and_resources_removed(self):
        bridge = DesktopAudioBridge(ROOT / 'build/audio-validation/self-capture')
        bridge.source_sink = bridge.sink_name
        try:
            bridge.start()
            bridge.poll(force=True)
            self.assertEqual(bridge.route, 'direct')
            self.assertIsNone(bridge.loopback)
            self.assertEqual(sum(bridge.owned(module) for module in bridge.listing()), 1)
        finally:
            bridge.stop()
        with pulsectl.Pulse('uuway-audio-cleanup-test') as pulse:
            self.assertFalse(any(sink.name == bridge.sink_name for sink in pulse.sink_list()))

    def test_real_desktop_monitor_wasapi_channels_switch_and_cleanup(self):
        directory = ROOT / 'build/audio-validation'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='live-', dir=directory) as temporary:
            work = Path(temporary)
            environment = dict(os.environ, TMPDIR=str(work), WINEPREFIX=str(work / 'wine'),
                               WINEDEBUG='-all', WINEDLLOVERRIDES='mscoree,mshtml=')
            environment.pop('WINEDLLPATH', None)
            subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                            str(ROOT / 'tests/probes/native_audio_playback.c'), '-lpulse', '-lm',
                            '-o', str(work / 'playback')], check=True, capture_output=True,
                           env=environment, timeout=30)
            for name in ('native_audio_loopback', 'native_audio_endpoint', 'native_audio_capabilities'):
                subprocess.run(['x86_64-w64-mingw32-gcc', '-std=c11', '-O2', '-Wall', '-Wextra',
                                '-Werror', '-municode', str(ROOT / f'tests/probes/{name}.c'),
                                '-ladvapi32', '-lole32', '-luuid', '-o', str(work / f'{name}.exe')],
                               check=True, capture_output=True, env=environment, timeout=30)
            bridge = DesktopAudioBridge(work / 'wine')
            with pulsectl.Pulse('uuway-audio-live-test') as pulse:
                original_sink = pulse.server_info().default_sink_name
                modules = []
                players = []
                recorder = None
                try:
                    names = ['uuway_test_' + work.name + suffix for suffix in ('_a', '_b')]
                    for name in names:
                        modules.append(pulse.module_load('module-null-sink',
                            f'sink_name={name} rate=48000 channels=2 '
                            'sink_properties="priority.session=0 priority.driver=0"'))
                    pulse.sink_default_set(names[0])
                    bridge.start()
                    environment['UURB_AUDIO_SINK'] = bridge.sink_name
                    wine = wine_bin_directory()
                    # 完整初始化真实 Wine prefix，随后测试进程间的设备选择。
                    with (work / 'wine.log').open('w') as log:
                        subprocess.run(['xvfb-run', '-a', str(wine / 'wine'), 'wineboot', '-u'],
                                       env=environment, stdout=log, stderr=log, check=True, timeout=60)
                        subprocess.run([str(wine / 'wineserver'), '-w'], env=environment,
                                       check=True, stdout=log, stderr=log, timeout=30)
                        missing = subprocess.run(['xvfb-run', '-a', str(wine / 'wine'),
                            str(work / 'native_audio_capabilities.exe')], env=environment,
                            capture_output=True, text=True, timeout=15)
                        self.assertEqual(missing.returncode, 1, missing.stdout + missing.stderr)
                        self.assertIn('audioses load failed: 126', missing.stdout)
                        component = fetch_component(ROOT / 'build/native-presenter/audioses.dll')
                        installed = install_component(work / 'wine', component)
                        self.assertEqual(install_component(work / 'wine', component), installed)
                        subprocess.run(['xvfb-run', '-a', str(wine / 'wine'),
                            str(work / 'native_audio_capabilities.exe')], env=environment,
                            stdout=log, stderr=log, check=True, timeout=15)
                        for name in names:
                            players.append(subprocess.Popen([str(work / 'playback'), name],
                                env=environment, stdout=log, stderr=log))
                        output = work / 'captured.pcm'

                        def winpath(path):
                            return 'Z:' + str(path).replace('/', '\\')

                        recorder = subprocess.Popen(['xvfb-run', '-a', str(wine / 'wine'),
                            str(work / 'native_audio_endpoint.exe'), winpath(work / 'native_audio_loopback.exe'),
                            winpath(output)], env=environment, stdout=log, stderr=log)
                        started = time.monotonic()
                        phase = 0
                        direct_player = None
                        while recorder.poll() is None and time.monotonic() - started < 20:
                            captured = output.stat().st_size if output.exists() else 0
                            if phase == 0 and captured >= 2 * 192000:
                                pulse.sink_default_set(bridge.sink_name)
                                direct_player = subprocess.Popen([str(work / 'playback'), bridge.sink_name],
                                    env=environment, stdout=log, stderr=log)
                                players.append(direct_player)
                                phase = 1
                            if phase == 1 and captured >= 4 * 192000:
                                direct_player.terminate()
                                direct_player.wait(timeout=5)
                                pulse.sink_default_set(names[1])
                                phase = 2
                            bridge.poll(force=True)
                            time.sleep(0.1)
                        self.assertEqual(recorder.wait(timeout=2), 0, (work / 'wine.log').read_text()[-4000:])
                        specification = importlib.util.spec_from_file_location('audio_trial', ROOT / 'scripts/uu-native-trial.py')
                        trial = importlib.util.module_from_spec(specification)
                        specification.loader.exec_module(trial)
                        self.assertIn(dict(event='native_audio_endpoint', code=0), trial.boot_events(work / 'wine.log'))
                        self.assertEqual(bridge.monitor, names[1] + '.monitor')
                        self.assertEqual(phase, 2)
                        samples = array.array('h', output.read_bytes())
                        self.assertGreater(len(samples), 48000 * 2 * 5)
                        for position in (48000 * 2, 48000 * 2 * 3, 48000 * 2 * 5):
                            chunk = samples[position:position + 48000 * 2]
                            for channel, expected, rejected in ((0, 440, 880), (1, 880, 440)):
                                values = chunk[channel::2]
                                rms = math.sqrt(sum(value * value for value in values) / len(values))

                                def amplitude(frequency):
                                    real = sum(value * math.cos(2 * math.pi * frequency * index / 48000)
                                               for index, value in enumerate(values))
                                    imag = sum(value * math.sin(2 * math.pi * frequency * index / 48000)
                                               for index, value in enumerate(values))
                                    return 2 * math.hypot(real, imag) / len(values)

                                signal = amplitude(expected)
                                self.assertGreater(rms, 500)
                                self.assertLess(rms, 4000)
                                self.assertGreater(signal, 1000)
                                self.assertLess(amplitude(rejected), signal * 0.02)
                    bridge.stop()
                    self.assertFalse(any(bridge.owned(dict(name=module.name, argument=module.argument))
                                         for module in pulse.module_list()))
                finally:
                    if recorder is not None and recorder.poll() is None:
                        recorder.terminate()
                        recorder.wait(timeout=5)
                    for player in players:
                        if player.poll() is None:
                            player.terminate()
                        player.wait(timeout=5)
                    subprocess.run([str(wine_bin_directory() / 'wineserver'), '-k'],
                                   env=environment, capture_output=True, timeout=10)
                    bridge.stop()
                    for module in reversed(modules):
                        pulse.module_unload(module)
                    deadline = time.monotonic() + 5
                    while original_sink not in {sink.name for sink in pulse.sink_list()}:
                        if time.monotonic() >= deadline:
                            raise RuntimeError('Original audio output did not return after cleanup')
                        time.sleep(0.05)
                    pulse.sink_default_set(original_sink)


if __name__ == '__main__':
    unittest.main()
