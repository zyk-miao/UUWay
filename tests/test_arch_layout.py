"""The pacman tree should contain only the runtime manifest's files."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage_arch', ROOT / 'packaging/stage-arch.py')
stage_arch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_arch)


class StageArchTests(unittest.TestCase):
    def test_runtime_files_and_command_links_without_debian_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'scripts/tool.py'
            source.parent.mkdir()
            source.write_text('#!/usr/bin/python3\n')
            dest = root / 'package'
            dest.mkdir()
            entries = [('scripts/tool.py', 'usr/lib/uuway/scripts/tool.py', 0o755),
                       ('not-present', 'usr/share/lintian/overrides/uuway', 0o644),
                       ('not-present', 'usr/share/doc/uuway/copyright', 0o644)]
            with patch.object(stage_arch, 'ROOT', root), \
                    patch.object(stage_arch.deb_manifest, 'files', return_value=entries), \
                    patch.object(stage_arch.deb_manifest, 'COMMANDS',
                                 {'usr/bin/uuway': '../lib/uuway/scripts/tool.py'}), \
                    patch.object(sys, 'argv', ['stage-arch.py', str(dest)]):
                stage_arch.main()
            installed = dest / 'usr/lib/uuway/scripts/tool.py'
            self.assertEqual(installed.read_bytes(), source.read_bytes())
            self.assertEqual(installed.stat().st_mode & 0o777, 0o755)
            self.assertEqual((dest / 'usr/bin/uuway').resolve(), installed)
            self.assertFalse((dest / 'usr/share/lintian').exists())

    def test_missing_required_file_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(stage_arch, 'ROOT', root), \
                    patch.object(stage_arch.deb_manifest, 'files',
                                 return_value=[('missing', 'usr/lib/uuway/missing', 0o644)]), \
                    patch.object(sys, 'argv', ['stage-arch.py', str(root)]):
                with self.assertRaises(FileNotFoundError):
                    stage_arch.main()


class AurInstallNoticeTests(unittest.TestCase):
    def notice(self, callback):
        script = ROOT / 'packaging/aur/uuway.install'
        result = subprocess.run(
            ['/bin/bash', '--noprofile', '--norc', '-c',
             'source "$1"; "$2" 1.2.0-2 1.2.0-1', 'notice', str(script), callback],
            env=dict(os.environ, PATH='/no-external-commands', BASH_ENV='/dev/null'),
            capture_output=True, text=True, check=True)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def test_recipe_and_srcinfo_include_install_script(self):
        directory = ROOT / 'packaging/aur'
        result = subprocess.run(
            ['/bin/bash', '--noprofile', '--norc', '-c',
             'source "$1"; printf "%s" "$install"',
             'recipe', str(directory / 'PKGBUILD')],
            capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, 'uuway.install')
        self.assertTrue((directory / result.stdout).is_file())
        self.assertIn('\tinstall = uuway.install\n', (directory / '.SRCINFO').read_text())

    def test_first_install_explains_setup(self):
        message = self.notice('post_install')
        self.assertIn('uuway setup --installer /path/to/uuyc.exe', message)
        self.assertIn('Plasma Wayland', message)
        self.assertIn('without sudo', message)
        self.assertNotIn('uuway refresh --yes', message)

    def test_upgrade_explains_manual_refresh_and_disconnect(self):
        message = self.notice('post_upgrade')
        self.assertIn('uuway refresh --yes', message)
        self.assertIn('Each configured desktop user', message)
        self.assertIn('without sudo', message)
        self.assertIn('disconnects active remote-control sessions', message)
        self.assertIn('does not upgrade the UU Windows client', message)


if __name__ == '__main__':
    unittest.main()
