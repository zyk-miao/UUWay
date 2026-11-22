import argparse
from pathlib import Path

from audio_session import fetch_component


parser = argparse.ArgumentParser(description='Download the pinned Microsoft Audio Session component')
parser.add_argument('destination', nargs='?', type=Path,
                    default=Path(__file__).resolve().parents[1] / 'build/native-presenter/audioses.dll')
arguments = parser.parse_args()
print(fetch_component(arguments.destination))
