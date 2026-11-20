# KDE display-off support (Plasma Wayland)

UU's 关闭被控端显示屏 (turn the controlled display off) uses an IDD virtual
monitor to keep the remote desktop available while physical outputs are
disabled. On Plasma Wayland, UUWay creates a KWin virtual output through the
ScreenCast portal, captures it through PipeWire and applies its layout through
KScreen. This document covers display-off support on Plasma 6.8 / KWin 6.8.

## How it works

1. The display service restores a saved ScreenCast Portal grant with
   `types=VIRTUAL`, creating one KWin output and receiving its PipeWire node.
   Its Windows name and device path stay stable across physical output changes.
2. UU's IDD requests create the output and select it through `SetDisplayConfig`.
   KScreen enables the virtual output before disabling the physical outputs.
   Restore requests accept both `0x14a0` and `0x10a0` flags.
3. Capture uses the owned PipeWire node and its actual dimensions through
   `UURB_CAPTURE_SIZE`. Separate SPA cursor metadata prevents duplicate cursors.
   The input worker reloads `input-map.json` without restarting UU or its input
   connection when the layout changes.
4. UU's `private_screen` setting (`1` off, `2`/`3` enabled) controls slot zero
   during connection setup and subsequent changes. Disabling display-off
   restores the physical layout. The client may retain its virtual-screen label.
5. `virtual-layout-recovery.json` records the physical layout. Owner-process
   death, closed video tracks, service shutdown and `ExecStopPost --recover`
   restore physical outputs before releasing the virtual output.

## Known limitations

* The service owns one virtual output at a time, at the resolution chosen in
  the Portal grant. It validates UU's IDD mode catalogue and advertises only
  the real output mode. Other requested resolutions fail before layout changes.
* KScreen changes the actual desktop layout. Recovery uses the saved journal;
  rotation, mirroring and Intel-only encoding retain their existing limits.

## Authorization

Before enabling virtual display reconfiguration, run this command in the KDE
session and select the matching resolution and remembered authorization:

```sh
python3 scripts/authorize-kde-virtual-display.py \
  --state "$HOME/.local/state/uurb/virtual-portal-state.json" \
  --width 2560 --height 1440
```

The command creates and closes a virtual output while keeping physical outputs
enabled. It rejects a different size before saving the token. The requested
dimensions must match the mode UU submits when entering its virtual topology.

## Verification

* `kde_display_lifecycle_live.c` and its Python runner exercise the production
  Win32 adapter against KDE: create, select, validate, restore with both flag
  combinations, and retain physical display identities and positions.
* `kde_virtual_capture.py` checks 2560×1440 DMA-BUF capture and Vulkan imports.
* `kde_input_map_live.py` checks live uinput map updates while adding and
  removing a Portal output, retaining the input connection and bridge runtime.
* Remote-client tests confirm ordinary DP-3 capture, display-off enable/disable,
  reconnect with display-off selected, continuous video and keyboard/mouse,
  and a single cursor.
