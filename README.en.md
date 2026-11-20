# UUWay for Manjaro KDE

**A NetEase UU Remote Linux host for Manjaro KDE Plasma Wayland.** This repository adapts [GaryOAO/UUWay](https://github.com/GaryOAO/UUWay) to Manjaro KDE: the official Windows host runs under Wine, while KDE's screen-cast Portal, PipeWire, NVIDIA GPU encoding and native input services connect it to the Linux desktop.

> This is mainly a **host**: it lets another computer or phone control this Linux machine. It can also open the UU window here to connect to other devices, pausing hosting meanwhile; see [Connecting to other computers](#connecting-to-other-computers).

[简体中文](README.md) · [KDE adaptation notes](docs/manjaro-kde.md) · [AUR build and test record](docs/aur-manjaro-kde.md)

## Status and limits

**KDE support is experimental.** On October 14, 2026, an independent Manjaro KDE machine completed an AUR source build, pacman install, UU sign-in, screen and input authorization, and bridge startup. Separate diagnostics captured 2560 × 1600 DMA-BUF frames and successfully encoded and decoded a nonblack H.264 image. `uuway doctor` reported no failures or warnings. **An end-to-end session from another device has not yet been accepted on that machine.** The original workstation displayed the desktop, but black flicker on pointer movement still needs a live retest; audio has also produced harsh noise and is not guaranteed to work.

| Feature | Manjaro KDE status |
| --- | --- |
| UU host, sign-in and background bridge | Installed and running on the test machine; live viewer test pending |
| Physical-screen capture and NVIDIA H.264 encoding | Independent capture and encode/decode checks passed |
| Pointer, keyboard and Chinese IME | Local input services and Fcitx5 add-on running; live viewer test pending |
| Text clipboard, remote terminal and file transfer | Inherited from upstream; not fully accepted on KDE |
| Multiple monitors | Up to 8, switchable from the viewer; each monitor is granted separately (verified with two monitors on 2026-10-26) |
| Remote resolution/scale changes | KDE profile is read-only; change these in local System Settings |
| Turn the controlled display off | Verified on Plasma 6.8 / KWin 6.8: enable, disable, reconnect with display-off selected, and continuous remote video, keyboard and mouse |
| UU Super Screen (Windows virtual monitor) | Unsupported; share the existing physical monitor |
| Control at the login screen | Unsupported; a logged-in Plasma Wayland session is required |
| Connect to another UU device from Linux | Supported; hosting pauses while the UU window is open (verified on 2026-10-26) |

The KDE profile streams **every active, non-mirrored, unrotated physical display** (up to 8; the primary is the first screen in UU). Monitors above 144 Hz are reported as 144 Hz; mirrored or rotated monitors are not streamed, and `uuway doctor` names any it leaves out. The Wine Xvfb display runs UU internally. Choose each real monitor as prompted when granting permission. Display-off uses a separately authorized KWin virtual output; see [KDE display-off support](docs/kde-virtual-display.md) for authorization and implementation. Headless operation remains unverified. See the [KDE adaptation notes](docs/manjaro-kde.md) for other limitations.

## Install

You need a Manjaro/Arch **Plasma Wayland** session, an NVIDIA GPU with NVENC and its driver, multilib enabled, and the official UU Remote **Windows installer**, obtained separately. The AUR build uses the host's pacman CUDA development headers. The verified test machine had CUDA 13.3 and system Wine 11.17. At runtime the package uses a separate SHA-256-verified WineHQ **11.0** under `/opt/uuway/wine-11.0`; it does not replace system Wine because the GPU bridge depends on this private protocol. The build downloads Wine archives and other sources and the installed package takes about 1.5 GB. See the [AUR documentation](docs/aur-manjaro-kde.md) for the full dependency and version boundary.

Install with an AUR helper:

```bash
yay -S uuway-git
```

Or build manually:

```bash
git clone https://aur.archlinux.org/uuway-git.git
cd uuway-git
makepkg -si
```

From a terminal in the **host machine's logged-in Plasma Wayland desktop**, run the wizard as your normal user (no `sudo` on `uuway setup`):

```bash
uuway doctor
uuway setup --installer /path/to/UURemote_Setup.exe
uuway doctor
```

Sign in in the UU window, select each monitor as prompted and save permission in KDE's screen-sharing dialog (a wrong choice is not saved; rerun `uuway setup --only portal` to choose again), then allow the separate input/clipboard request. Input rule installation may require administrator confirmation. The package contains **neither** the UU installer nor account data. Never copy a Wine prefix, login data or Portal grant from another machine.

The **UUWay Console** is available from the application menu. The KDE tray starts at desktop login and can start, restart or stop the local host. Use `uuway doctor` for status or `systemctl --user status uu-native-bridge uu-native-text uu-native-display` for service details. Upgrade with pacman/an AUR helper, then run `uuway refresh`. Ubuntu `.deb`/`apt` commands such as `uuway update install` and `rollback` **do not apply on Manjaro**; the source `./install.sh` is not the Manjaro installer either.

### Connecting to other computers

UU allows one window per Wine prefix, and the host bridge normally holds it. To control another device from this machine, open **UU Remote (control other computers)** from the application menu, the Console overview's "连接其他电脑" card or the tray's "连接其他电脑…" item, or run `uuway open`. UUWay pauses hosting and opens the UU window; when you are done, **quit UU from its tray icon** (closing the window only hides it to the tray), and hosting resumes about 15 seconds later. Phones and other devices cannot connect to this machine meanwhile.

`uuway autologin on` configures upstream's **GDM** only. It does not configure SDDM, commonly used by KDE. If you need unattended availability after reboot, assess the security implications and configure desktop auto-login separately. UUWay is offline at the login screen.

### Screen capture delivers no frames

A successful screen-sharing grant does not prove PipeWire is delivering frames. On the test machine, only a dummy audio output remained and capture stopped delivering frames. Restarting WirePlumber restored real audio devices and capture. **This interrupts active media connections**; run it only when appropriate:

```bash
systemctl --user restart wireplumber.service
uuway setup --only portal --force portal
```

Choose each physical monitor again as prompted. See the [AUR troubleshooting notes](docs/aur-manjaro-kde.md).

## Design and credits

UU's official Windows host continues to handle accounts, connections and bitrate negotiation. UUWay connects desktop capture, encoding and input to native Linux components. This fork adds a Plasma Wayland read-only display profile, an Arch-native AUR build and KDE tray integration. See the [design notes](docs/design.md) and [version review](docs/releases/4.42.0.2770-native-review.md).

Upstream: [GaryOAO/UUWay](https://github.com/GaryOAO/UUWay); earlier work: Lachlan Chen's [uu-remote-ubuntu-bridge](https://github.com/lachlanchen/uu-remote-ubuntu-bridge). Thanks to the original authors and to Wine, DXVK, PipeWire and their contributors. Ubuntu/GNOME users should follow the upstream instructions, **not** install an upstream `.deb` as this fork's Manjaro package.

The main project license is [AGPL-3.0](LICENSE); bundled third-party components retain their own licenses. This unofficial project is not affiliated with NetEase and does not distribute the official UU software.
