import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request


VERSION = '10.0.19041.264'
SHA256 = '25e322822aa08b7532bd7b17ef6dccf011feabcb3af4c6100d56299e6a54d568'
SIZE = 1560408
URL = 'https://msdl.microsoft.com/download/symbols/audioses.dll/07B4922F180000/audioses.dll'


def verify_component(path):
    path = Path(path)
    if path.stat().st_size != SIZE or hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Unexpected Microsoft Audio Session component')


def fetch_component(destination):
    destination = Path(destination)
    if destination.exists():
        verify_component(destination)
        return destination
    if destination.is_symlink():
        raise ValueError('Audio component destination is a dangling symlink')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=60) as response:
        data = response.read(SIZE + 1)
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Microsoft Audio Session download verification failed')
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.audioses-') as temporary:
        temporary.write(data)
        temporary.flush()
        os.fsync(temporary.fileno())
        os.link(temporary.name, destination)
    return destination


def install_component(prefix, source):
    verify_component(source)
    destination = Path(prefix) / 'drive_c/windows/system32/audioses.dll'
    if destination.exists():
        verify_component(destination)
        return destination
    if destination.is_symlink():
        raise ValueError('Audio Session dependency is a dangling symlink')
    if not destination.parent.is_dir():
        raise ValueError('Audio Session dependency requires an initialized Wine prefix')
    # 系统组件保留在 prefix 中，运行时重启时继续校验相同版本。
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.uuway-audioses-') as temporary:
        with Path(source).open('rb') as stream:
            shutil.copyfileobj(stream, temporary)
        temporary.flush()
        os.fsync(temporary.fileno())
        verify_component(Path(temporary.name))
        os.link(temporary.name, destination)
    return destination
