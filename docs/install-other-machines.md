# Install this fork on another computer

The source in this fork includes the experimental KDE capture fixes and the
UUWay tray. An upstream 1.2.0 release binary does **not** include changes made
in this fork. Build from the desired commit; do not mix an older release's
native capture or Wine DLL binaries with this checkout. UU's Windows installer
must be obtained separately from the official provider.

Do not copy your original computer's Wine prefix, account settings, Portal
restore tokens, private keys, or `~/.local/state/uurb` to the new computer.
Each desktop needs its own UU login and screen/input authorization.

## Ubuntu 24.04, GNOME Wayland

Use a logged-in graphical Wayland session and an NVIDIA GPU with NVENC and the
proprietary driver. On the target computer, with Docker available, clone this
fork and build its package in an Ubuntu 24.04 container:

```bash
git clone https://github.com/zyk-miao/UUWay.git
cd UUWay
packaging/build-deb.sh
sudo apt install ./build/deb/uuway_*_amd64.deb
uuway setup --installer "$HOME/Downloads/UURemote_Setup.exe"
uuway doctor
```

Run `uuway setup` as your normal desktop user, **not** with `sudo`. Sign in to
the UU window, approve the screen-sharing dialog (select the physical monitor
and remember the permission), and approve the separate input/text dialog.
The console is available from the application menu; the tray starts at desktop
login. The bridge only comes online after the desktop session has logged in.
This is a build from the fork's source, not an automatically published or
signed release. Review the code and package before installation.

Without Docker, see [build.md](build.md) for Ubuntu source-build requirements.

## Manjaro KDE Wayland (experimental)

Use the native `packaging/aur/PKGBUILD`; a fresh source build and pacman
installation were verified on an independent Manjaro KDE machine on
2026-10-14. Live remote-control testing on that machine remains pending.
Ubuntu `.deb` files and `./install.sh` must not be run as Manjaro installers.
The tested KDE profile requires one active, unmirrored, unrotated
physical display at origin (0, 0), a working KDE screen-cast Portal, NVIDIA
NVENC, `/dev/uinput` access, and a WineHQ **11.0** runtime. The system's newer
Wine version cannot be silently substituted. KDE's virtual display is not a
replacement for this physical-output profile. See
[native AUR build status and host package versions](aur-manjaro-kde.md) before
installing on a different Manjaro computer. The new package builds native
components using the machine's CUDA headers and installs private Wine 11.0
under `/opt/uuway/wine-11.0`; it preserves the system Wine and CUDA.

Before attempting a fresh KDE installation:

1. Clone this fork on the target and check its environment from the logged-in
   Plasma Wayland desktop with `/usr/bin/python3 scripts/uuway_cli.py doctor`,
   `kscreen-doctor -j` and `nvidia-smi -L`.
2. Enable multilib and install `uuway-git` with an AUR helper, or clone
   `https://aur.archlinux.org/uuway-git.git` and run `makepkg -si`. A copy of
   the recipe is kept at `packaging/aur/PKGBUILD`. It declares the
   required compiler, CUDA, Wine headers and runtime dependencies; Docker is
   not required. See [aur-manjaro-kde.md](aur-manjaro-kde.md) for build details.
3. Run `uuway doctor` from the Plasma desktop. The package installs the
   console/menu identity and input rule before screen-sharing authorization.
   Do not enable the GNOME/Mutter display guardian on KDE.
4. Once all prerequisites are verified, use the target machine's own official
   Windows UU installer and run `uuway setup
   --installer /path/to/UURemote_Setup.exe` as the logged-in user. Sign in and
   grant screen/input access **on that machine**. Check the resulting service
   with `uuway doctor`.

The earlier manual Ubuntu-container trial remains documented in
[manjaro-kde.md](manjaro-kde.md), alongside hardware-specific results and the
desktop audio configuration. Avoid copying its private build cache or installed
prefix to another computer.
