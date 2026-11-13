# Manjaro KDE: native AUR build

`packaging/aur/PKGBUILD` builds the DLLs, workers, DXVK patch, helpers and
Fcitx add-on from source on Arch/Manjaro. It stages the same runtime file list
as the Debian package, without Debian packaging or installing files from the
maintainer's machine. On 2026-10-14 a fresh `makepkg -C --holdver` source build
completed on an independent Manjaro KDE machine, and its pacman package was
installed there. This was a fresh build directory, not a clean chroot test.
The verified recipe was published as **`uuway-git`** on AUR on 2026-10-14.
Live remote-control acceptance remains pending; KDE support is experimental.

## Build dependencies and version boundary

The native compiler, MinGW, Meson, Ninja, Vulkan/GLSL, Fcitx and CUDA headers
come from pacman. The tested build uses the system CUDA 13.3 headers and stub
at `/opt/cuda`; CUDA 12.1 retains its original three-argument context API.
The compatibility shim selects CUDA 13.3's four-argument API at compile time.
The resulting binary references the API provided by the installed NVIDIA
driver; building successfully does not guarantee all NVENC/display operations
on another GPU/driver. Verify the driver before using UUWay.

The native Wine GPU adapter uses Wine **11.0** private server protocol 930.
The system Wine 11.17 cannot be substituted for that runtime. `makepkg` obtains
the SHA-256-verified official WineHQ 11.0 main, amd64 and i386 `.deb` files as build inputs and
places its Wine files under `/opt/uuway/wine-11.0` inside the pacman package.
This is **not** an Ubuntu build or a `.deb` installation, and does not replace
`/usr/bin/wine`. The Arch Wine package supplies generated development headers
for building; pinned Wine 11.0 source provides its private server header.
DXVK and its submodules are also fixed to reviewed revisions. No official UU
installer, account credentials, Wine prefix or Portal tokens are packaged.

## Build machine (2026-10-14)

An independent Manjaro KDE test machine has an NVIDIA
RTX 4090 Laptop GPU, driver `610.57.04`, Wine `11.17-1`, CUDA `13.3.1-1`,
Fcitx5 `5.1.22-1` and GCC `16.2.1`. We installed Arch build dependencies
`mingw-w64-gcc`, `meson`, `ninja` and `vulkan-headers`. Its native source build
completed, the CUDA context API was exercised against the real driver, and
the installed runtime produced a verified 26-component user bundle. Pacman
reported 2,982 installed files with none missing, and the GTK console smoke
test passed. The official UU 4.42.0.2770 installer was installed into a fresh
prefix on that machine; its unpatched server matches the reviewed SHA-256.
The native first-login helper opened visible UU windows, the KDE tray was
registered, and UU's codec detector completed H.264 and HEVC first-frame
encoding on the system CUDA driver. The user completed UU login and screen,
keyboard and clipboard authorization on that machine. Package
`1.2.0.r73.gc382146-1` completed setup and started the bridge and text services.
An eight-second native screen capture delivered 642 DMA-BUF frames at
2560 x 1600. A separate H.264 hardware-encoding check encoded and decoded
362 frames and confirmed a nonuniform image, without persistent recording.
This does **not** establish live UU remote-control acceptance.

On the original workstation (RTX 3060 Laptop, same Wine and CUDA pacman
versions), the running bridge still uses a separate private Wine 11.0 and
the older CUDA 12.1-built capture binary. Do not confuse installed toolkit
versions with the versions used to build a running executable.

## Installation and testing

Enable the distribution's multilib repository first: the pinned Wine runtime
requires 32-bit libraries. Build as an ordinary user with the system CUDA
toolkit and Wine development headers installed. AUR helpers can install the
declared dependencies. The source downloads include roughly 250 MB of Wine
archives; the resulting package occupies about 1.5 GB installed.

The recipe and generated `.SRCINFO` are also kept in `packaging/aur/` in this
GitHub repository. Install with an AUR helper (`yay -S uuway-git`), or build
the AUR recipe directly:

```bash
git clone https://aur.archlinux.org/uuway-git.git
cd uuway-git
makepkg -si
```

Then obtain the official Windows UU Remote installer and complete setup from
a terminal in the **target machine's** logged-in Plasma Wayland desktop:

```bash
uuway doctor
uuway setup --installer /path/to/UURemote_Setup.exe
uuway doctor
```

`setup` may require interactive desktop login and consent; do not provide UU
credentials to the package builder. On KDE, first login uses the same native
bootstrap as the bridge with temporary verified loader links. It restores the
visible UU window and removes its own links and registry changes before
requesting Portal authorization. This is needed when a plain Wine launch
does not open the UU login window. Keep one physical output active during
initial tests. AUR upgrades are handled by pacman/AUR tools followed by
`uuway refresh --yes`; `uuway update install`/`rollback` remain disabled on Arch.
The package prints a setup reminder after installation and a refresh reminder
after upgrades. Run the command as the ordinary desktop user in a logged-in
Plasma Wayland session, not with `sudo`. Each configured user needs to refresh
their own runtime; this restarts remote hosting and disconnects active remote
sessions. The reminder does not run the refresh automatically, and upgrading
the AUR package does not upgrade the official UU Windows client inside Wine.
The build does not rely on ignored `build/` files or Docker. Private Wine
retains its upstream layout under `/opt/uuway`, which produces a generic
`namcap` ELF-location warning; its upstream binaries also retain WineHQ's
hardening settings. Scanner/camera and Wine development utilities are optional
and are not part of the UU remote-control path. See
[manjaro-kde.md](manjaro-kde.md) for known KDE and audio limitations.

## First setup troubleshooting

The setup and desktop-image registry helper disable Wine Mono and Gecko
loading because those components are not required by this path. If an older
package displays a Wine Mono installer, completing that dialog does not
replace Wine itself. Upgrade to the current AUR source before retrying setup.
The login stage also stops the prefix's automatically started UU service
before waiting for Wine to exit, so a successful login can advance to screen
authorization.

On the test machine, screen authorization succeeded but neither the native
probe nor GStreamer received frames. WirePlumber was running, yet its device
and connection policy was stalled; only a dummy audio output remained.
Restarting WirePlumber restored both real audio devices and screen capture:

```bash
systemctl --user restart wireplumber.service
uuway setup --only portal --force portal
```

This restart interrupts current media connections. UUWay does not restart the
desktop's media manager automatically. A saved Portal grant alone does not
prove that capture is delivering frames; retry the capture check before
diagnosing the UU presentation path.
