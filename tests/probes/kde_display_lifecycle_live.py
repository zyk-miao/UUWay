import argparse
import configparser
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from desktop_backend import wine_bin_directory
from native_runtime_state import read_private


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--socket', type=Path, required=True)
    arguments = parser.parse_args()
    directory = arguments.binary.resolve().parent
    for name in ('uurb-native-display-loader.dll', 'uurb-native-display.dll.so'):
        shutil.copyfile(arguments.bundle / 'runtime' / name, directory / name)
    prefix = directory / 'wine-ccd'
    temporary = directory / 'wine-temp'
    for path in (prefix, temporary):
        path.mkdir(mode=0o700, exist_ok=True)
    config = read_private(Path.home() / '.config/uurb/native-runtime.json')
    settings = configparser.ConfigParser(interpolation=None)
    with (Path(config['prefix']) / 'drive_c/ProgramData/Netease/GameViewer/user_setting.ini').open() as source:
        settings.read_file(source)
    expected_exclusive = settings['global'].get('private_screen') in ('2', '3')
    environment = dict(os.environ, WINEPREFIX=str(prefix), TMPDIR=str(temporary), WINEDEBUG='-all',
                       WINEDLLOVERRIDES='mscoree,mshtml=')
    environment.pop('WINEDLLPATH', None)
    wine = wine_bin_directory()
    try:
        result = subprocess.run([str(wine / 'wine'), str(arguments.binary.resolve()),
                                 str(arguments.socket), str(int(expected_exclusive))],
                                env=environment, timeout=60)
    finally:
        subprocess.run([str(wine / 'wineserver'), '-k'], env=environment, check=True, timeout=10)
        subprocess.run([str(wine / 'wineserver'), '-w'], env=environment, check=True, timeout=10)
    raise SystemExit(result.returncode)
