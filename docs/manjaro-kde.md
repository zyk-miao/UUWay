# Manjaro KDE Wayland (experimental)

The native input/capture worker streams **every active, unmirrored, unrotated**
Plasma output (up to 8) read via `kscreen-doctor -j`. On KDE the display service
is read-only (`native_display_kscreen.py`): it reports the outputs to UU's
Windows display shim, each captured through its own saved Portal grant, and
refuses mode, scale and layout writes; Super Screen is unavailable. Absolute
input is remapped from the Windows layout onto each output's share of KWin's
uinput axes. Change resolution/scale locally in System Settings. Portal permission and native GPU
capture have been verified on this host. The actual UU session displayed the
desktop; it still needs a manual retest after the cursor stability fix. This
is not a supported release target.

As of 2026-10-14, the active UUWay bridge still uses the private Wine 11.0
runtime: the running `wineserver` is under `~/.local/opt/uuway/wine-11.0/`.
`pacman -Q wine` reports 11.17 and `pacman -Q cuda` reports 13.3.1, but those
are the installed system packages, **not** evidence that UUWay has been
rebuilt and remotely tested with Wine 11.17 or CUDA 13.3 headers. See
[the Arch-native AUR build status](aur-manjaro-kde.md) for package versions.

For a new computer, begin with [the cross-machine installation checklist](install-other-machines.md).
The dated observations below describe one test host; they are not a portable
installer, and that host's UU account, Portal tokens and Wine prefix must not
be copied to other machines.

## Bidirectional Clipboard

KWin shares a native Wayland clipboard with Xwayland clients only while an X11 window is active.
UUWay therefore listens directly through `ext-data-control-v1` where available, including this
host's KWin 6.7.4. This fixes desktop-to-controller copies while a native KDE application is
focused. The `wayland` package supplies the runtime library and protocol scanner used during
the AUR build. Compositors without the protocol retain the existing Xwayland bridge.

Run `/usr/bin/python3 -m unittest tests.test_clipboard_bridge tests.test_clipboard_wayland`
to check the X11 fallback and an isolated headless KWin session. The native tests cover UTF-8
text, image and file-list formats, concurrent copies, and echo/transient filtering. Actual UU
controller-side paste still requires a manual remote test.

## Check this computer

Run these from the logged-in Plasma **Wayland** session as your normal user:

```bash
/usr/bin/python3 scripts/uuway_cli.py doctor
kscreen-doctor -j
nvidia-smi -L
```

The doctor accepts KDE Wayland and lists the streamed outputs, naming any mirrored or rotated ones it leaves out. It also reports
missing Wine, NVENC libraries, uinput permissions, portal consent, and services.
`./install.sh` deliberately stops before apt on Manjaro. The `.deb` release and
`uuway update install/rollback` use dpkg/apt and must not be installed here.

## Upgrading From Single-Screen Capture

After updating the package, run `uuway refresh` from the logged-in Plasma
session. The portal step identifies which output the legacy
`portal-probe.json` grant shares and requests grants only for other missing
outputs. It keeps the rotated legacy token at its original path until the
new runtime configuration has been staged successfully, then moves it to
`portal-probe.<connector>.json`. It does not duplicate the token.

A portal-only run (`uuway setup --only portal`) prepares the migration but
leaves the old runtime's grant in place; finish with `uuway refresh`. A
packaging failure leaves the old bridge running. If runtime staging fails
or is interrupted, UUWay restores the prior runtime configuration and user
units, retains the current valid grant, and restarts the bridge only if it
was running before the switch. If automatic recovery fails, the command
reports that failure rather than claiming the service was restored. Fix the
reported cause and retry `uuway refresh`.

## Prerequisites for a source trial

1. Obtain the official Windows UU installer yourself. The project does not ship it.
2. The native package provides **WineHQ stable 11.0** at
   `/opt/uuway/wine-11.0/bin/`. For a manual source trial, provide it at
   `/opt/wine-stable/bin/` (wine, wineboot,
   wineserver and winegcc). The currently available Manjaro `wine` package may
   have a different version and layout. Do not silently substitute it: the
   private capture bridge is built against the 11.0 Wine server protocol.
   A separate user installation at `~/.local/opt/uuway/wine-11.0/bin/` is also
   detected when the system WineHQ path is absent.
3. For a native Manjaro build use the [AUR recipe](aur-manjaro-kde.md) and
   verify ELF dependencies on the target. It uses the system CUDA 13.3 headers
   and the pinned Wine 11.0 private runtime, not system Wine 11.17. The old
   Ubuntu source-build instructions in [build.md](build.md) still use CUDA 12.1.
4. Ensure `xdg-desktop-portal-kde`, PipeWire, `kscreen-doctor`, `/usr/bin/python3`
   with `dbus` and `gi`, `xvfb-run`, and a working `/dev/uinput` are present.
   The pacman package supplies the input rule and console identity. For a
   manual source trial, install `config/70-uurb-native-input.rules` only after
   reviewing its permissions. Install the console with
   `scripts/install-uu-settings.py` before authorizing capture: the KDE Portal
   uses its `uuway.desktop` identity to remember sharing permissions.

Instead of compiling, the native files can be extracted from the project's
official release after verifying its SHA256SUMS. Do not install the Debian
package with a package manager on Manjaro. Check that the release's native
sources match the checkout and that every extracted ELF dependency resolves.
Those older prebuilt files were compiled with CUDA 12.1; they do not need the
toolkit headers to run. A new Arch-native build can use the verified CUDA 13.3
headers without replacing the host's installed CUDA package.

With a *verified compatible* built tree and WineHQ 11.0 already in place,
`/usr/bin/python3 scripts/uuway_cli.py setup --installer /path/to/UURemote_Setup.exe`
can stage a KDE read-only-display service. `--dry-run` shows the setup actions.
Do not enable `uu-native-display.service` on KDE: it talks only to Mutter.

On this checkout's host (RTX 3060 Laptop, Plasma Wayland), the topology
parser and service profile have been tested. The installed `/usr/bin/wine`
reports **11.17** and `/opt/cuda/bin/nvcc` reports **13.3**, with headers at
`/opt/cuda/include/cuda.h`. These are not the pinned Wine 11.0 protocol and
CUDA 12.1 headers used to build the existing GPU bridge. Do not symlink
the system Wine/CUDA into the pinned paths: the Wine private handle protocol
and CUDA symbol versions are part of the compatibility boundary. At that
initial check WineHQ 11.0 and CUDA 12.1 headers were absent; the subsequent
installation below added private Wine and used pinned build headers without
changing the system Wine/CUDA packages.

On 2026-10-14 an independent Manjaro host compiled the new AUR-targeted
sources against its system CUDA 13.3 after an explicit API compatibility fix.
This does not mean the older running bridge on this computer was replaced.

## Local installation on 2026-10-13

WineHQ 11.0 was installed separately in `~/.local/opt/uuway/wine-11.0`.
The official UU 4.42.0.2770 installer and server match the hashes recorded in
the project's release review. The initial native artifacts were extracted from
UUWay 1.2.0 after checking SHA256SUMS. That release does not include the later
source and binary fixes described below; do not use its binaries with this
fork to set up another machine.
All eight native ELF dependencies resolve on this host. Xvfb, xclip, and the
missing 32-bit font libraries were extracted from signed Manjaro packages to
`~/.local/lib/uuway-tools`; the existing system Wine and CUDA were preserved.

The console, Fcitx5 add-on, Wine path mappings, and KDE read-only service units
are installed. A bridge drop-in supplies the user tools and 32-bit library
path. The Fcitx5 add-on loads and its private socket is available.

For a fresh installation, open **UUWay 首次登录** from the application menu to finish account login and
desktop consent. The local setup helper starts UU on the visible desktop,
waits for account configuration, removes its temporary loaders and registry
settings, requests screen-sharing consent, and then starts the normal user
services. The first screen-sharing request timed out without consent; no
authorization token was fabricated. Restart the setup helper with:

```bash
systemctl --user restart --no-block uuway-first-login.service
```

The helper and independent text service reference this checkout, so keep it
at its current path. The ordinary bridge uses an immutable per-user bundle.

## Black screen investigation on 2026-10-13

Account login completed, but the first actual UU remote connection showed only
the Wine application desktop. The capture broker had
no first-frame acknowledgments. Anonymous Portal clients were not restoring
KDE consent, so each short-lived UU capture attempt waited for a new dialog.
The capture wrapper now registers the installed `uuway.desktop` application
before requesting a session. After one explicit user grant with the remember
option, subsequent authorized sessions started in 9-13 ms without a new dialog.

KWin also delivered repeated/backward source timestamps. NVENC and the GPU
transport require increasing timestamps; the worker now recycles stale buffers
without encoding or substituting a clock. The worker was rebuilt in the isolated
Ubuntu container with the pinned CUDA 12.1 and NVENC headers. A 1920x1080 H.264
sample passed independent decoding and nonuniform-image checks. The installed
broker, metadata cursor mode, and native GPU consumer then passed a separate
23-frame relay/decode check with a first-frame acknowledgment. These diagnostics
use anonymous temporary compressed data and do not save desktop recordings.

The text supervisor now checks the system Python executable identity instead of
hardcoding Python 3.12, which rejected this host's Python 3.14. Keyboard/clipboard
Portal consent may need one new grant under the registered application identity.

## Desktop audio

Desktop audio uses a dedicated PulseAudio output and Wine WASAPI loopback at
48 kHz stereo. The route follows the desktop's default output and also accepts
applications playing directly into the dedicated output. The runtime includes
the verified Microsoft Audio Session dependency needed by UU's Core Audio
probe. Enable sound in the controller's session controls. Windows UU 4.48.1
playback was confirmed on 2026-11-23; real PulseAudio/Wine tests cover capture,
output changes and cleanup. See [the audio design](design.md#desktop-audio).

## Further video investigation

The next remote test confirmed working pointer movement/clicks but still had a
black image. UU's log identified a separate Windows-side failure:
`Pinned Wine Unix runtime is not loaded`, followed by DXGI `E_FAIL` and encoder
initialization failures. The private Wine FD adapter hardcoded the Ubuntu
installation at `/opt/wine-stable`, so it could not resolve this host's relocated
Wine 11.0 runtime. It now locates the unique already-loaded
`x86_64-unix/ntdll.so` through the dynamic loader and uses `RTLD_NOLOAD`;
the existing Wine 11.0 version and server protocol 930 checks remain in place.
Both the DXGI capture and Windows NVENC backends were rebuilt. An isolated real
Windows PE client passed DXGI acquisition, D3D11 materialization, Windows NVENC,
and independent decoding of 362 nonuniform 1920x1080 H.264 frames.
The same PE client also passed the actual DXVK `DuplicateOutput1` hook, output
geometry and negative-call checks, and decoded another 344 desktop frames.
The rebuilt backends were packaged into a new immutable runtime and the bridge
was restarted; the independent text service retained its live authorization.

Keep selecting the **physical screen** for desktop sharing. The private Xvfb
display holds UU's own Windows UI; it is not the remote desktop source. Adding
a KDE virtual output is outside this physical-output input/display profile and
does not address the Wine runtime-path error.

The following manual test displayed the desktop, but mouse movement repeatedly
returned to the black Wine desktop. The live broker recorded producer exits
after successful first-frame acknowledgments while the same UU consumer stayed
connected. Cursor metadata negotiation requested a fixed 384x384 allocation,
which did not match KWin's smaller allocation: an owned fullscreen cursor
fixture changed shapes while the shared cursor snapshot remained inactive.
With pointer motion enabled, the old installed producer reproduced the failure
after two movements: `Invalid/non-DMA-BUF plane metadata; refusing fallback`.
The producer now negotiates a bounded size range. It also handles KWin's
cursor-only chunks marked `SPA_CHUNK_FLAG_CORRUPTED` with nonzero allocation
sizes, without importing their video contents. Corrupted headers and mixed
usable-video planes still cannot enter that cursor-only path.

The rebuilt producer passed a 12-second physical-output metadata test with
28 owned pointer movements, 21 cursor shape updates, and 149 independently
decoded nonuniform 1920x1080 H.264 frames without exiting. The fixture stops
desktop animation after three seconds, so this frame count is not an animated
desktop frame-rate benchmark. A separate shape-only run decoded 695 frames.
The bounded cursor parser and broker checks passed; the cursor parser was also
compiled against this host's SPA headers because the pinned test sysroot is
absent. The actual UU session still needs a manual mouse-movement retest after
installing this producer. The updated immutable runtime was installed and the
bridge restarted, retaining metadata cursor mode and the physical output.

## Local Tray Controls

The console now exposes an AppIndicator tray using the host's installed
`AppIndicator3` or `AyatanaAppIndicator3` GTK bindings. On this Manjaro KDE host,
`AppIndicator3` was already available; no system packages were changed. The
console installer writes a managed `~/.config/autostart/uuway-tray.desktop`
entry referencing its immutable console release. It starts hidden with `--tray`
and shares the same single application instance as the menu's console entry.

The tray shows the local bridge status and offers console, start, restart,
stop, stop-and-exit, and tray-only exit actions. Closing the console hides it
while retaining input drafts. Stopping/restarting asks before disconnecting the
remote session; a failed stop keeps the tray available. Tray-only exit leaves
the bridge running. The tray was started locally without restarting the bridge,
and KDE's StatusNotifierWatcher and DBusMenu reported the UUWay item and all
expected enabled/disabled menu actions.

## Topology polling and accessibility

The KDE topology helper removes `QT_LINUX_ACCESSIBILITY_ALWAYS_ON` and
`AT_SPI_BUS_ADDRESS` from its child environment. Qt treats the first variable as
force-enabled whenever it exists, including when its value is `0`; an explicit
bus address also forces a connection. Geometry queries should follow the desktop's
accessibility policy. The parent environment and desktop settings are preserved.

The opt-in regression below runs real read-only geometry queries and observes
only accessibility connection metadata. It includes a forced-registration
positive control, then checks that regular topology queries return the same
geometry without registering accessibility clients. It requires a live Plasma
Wayland session with desktop accessibility disabled and does not change that policy.

```bash
UUWAY_LIVE_DESKTOP_TESTS=1 /usr/bin/python3 -m unittest tests.test_desktop_backend_live -v
```
