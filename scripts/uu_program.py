"""Resolve UU's program directory across the layouts its updater produces.

UU's own updater renames the live ``bin`` to ``<old-version>`` and unpacks the
new payload into ``<new-version>``, intending to rename that back to ``bin``
afterwards. Under Wine the last step can be skipped, which leaves no ``bin`` at
all -- or a ``bin`` symlink aimed at a payload the installer has since deleted.
Either way UU still runs, so refusing to start would describe the symptom
rather than the cause.

A real ``bin`` directory belongs to UU and is authoritative. The ``bin``
symlink this project installs is not, because after another update it still
points at the previous payload; the newest version directory wins instead.
"""
import re
from pathlib import Path

UU_VERSION_DIRECTORY = re.compile(r'[0-9]{1,5}(?:\.[0-9]{1,5}){3}')
SERVER_EXE = 'GameViewerServer.exe'


def uu_program_directory(app):
    """The directory holding UU's server payload."""
    app = Path(app)
    bin_dir = app / 'bin'
    if bin_dir.exists() and not bin_dir.is_symlink():
        if (bin_dir / SERVER_EXE).is_file():
            return bin_dir
        raise RuntimeError('UU bin exists but has no server payload: ' + str(bin_dir))
    candidates = []
    try:
        for entry in app.iterdir():
            if entry.is_symlink() or not entry.is_dir() or not UU_VERSION_DIRECTORY.fullmatch(entry.name):
                continue
            if (entry / SERVER_EXE).is_file():
                candidates.append(entry)
    except OSError:
        candidates = []
    if not candidates:
        raise RuntimeError('Official UU program directory not found: neither bin/ nor a <version>/ payload exists')
    return max(candidates, key=lambda item: tuple(int(part) for part in item.name.split('.')))


def ensure_program_entrypoint(app, log=None):
    """Make ``app/bin`` point at the live payload, repairing a stale or dangling link.

    Every other component addresses UU through ``bin/``, including the loader
    links installed beside it, so keeping that name valid is what makes an
    unfinished UU update recoverable instead of fatal. The link stays relative
    so moving the prefix keeps it working.
    """
    app = Path(app)
    program = uu_program_directory(app)
    entrypoint = app / 'bin'
    # Already aimed at the current payload: leave it alone, so a restart does
    # not churn the link (and log a repair) on every start.
    if entrypoint.is_symlink() and entrypoint.readlink() == Path(program.name):
        return entrypoint
    if program == entrypoint:
        return program
    if entrypoint.is_symlink():
        # Dangling or aimed at a retired payload; neither can be kept.
        entrypoint.unlink()
    elif entrypoint.exists():
        raise RuntimeError('UU bin exists but has no server payload: ' + str(entrypoint))
    entrypoint.symlink_to(program.name)
    if log is not None:
        log('uu_program_entrypoint_restored', target=program.name)
    return entrypoint
