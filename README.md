# UUWay for Manjaro KDE

**在 Manjaro KDE Plasma Wayland 上运行网易 UU 远程的 Linux 被控端。** 本仓库是 [GaryOAO/UUWay](https://github.com/GaryOAO/UUWay) 的 Manjaro KDE 适配分支：通过 Wine 运行官方 Windows 被控端，并使用 KDE 屏幕共享 Portal、PipeWire、NVIDIA GPU 编码及原生输入服务对接 Linux 桌面。

> 本项目主要是**被控端**：让其他电脑或手机远程连接本机。也可以在本机临时打开 UU 窗口去连接其他设备，期间本机暂停被控，见下文[连接其他电脑](#连接其他电脑)。

[English](README.en.md) · [Manjaro KDE 适配记录](docs/manjaro-kde.md) · [AUR 构建与测试记录](docs/aur-manjaro-kde.md)

## 状态与限制

**KDE 支持仍属实验性。** 2026-10-14 在一台独立的 Manjaro KDE 测试机上，已验证 AUR 源码构建、pacman 安装、UU 登录、屏幕及输入授权、桥接服务启动，以及 2560 × 1600 桌面的 DMA-BUF 采集和 H.264 编码/解码（画面非全黑）。`uuway doctor` 为 0 失败、0 警告。**这不等于已完成从另一台设备发起的端到端远控验收。** 本机曾显示画面，但鼠标移动引发的黑屏闪烁仍待真实远控复测；声音也曾出现刺耳噪声，不能保证音频可用。

| 功能 | Manjaro KDE 状态 |
| --- | --- |
| 本机作为 UU 被控端、登录与后台服务 | 已在测试机安装并启动；远控连接待验收 |
| 物理屏幕采集、NVIDIA H.264 硬件编码 | 独立采集及编码/解码测试通过 |
| 鼠标、键盘与中文输入 | 本机输入服务及 Fcitx5 插件已启动；实际远控需测试 |
| 文本剪贴板、远程终端与文件传输 | 已接入原项目功能；KDE 上的完整远控流程尚未验收 |
| 多显示器 | 最多 8 块屏，UU 端可切换；每块屏单独授权（2026-10-26 双屏实机验证） |
| 远程调整分辨率/缩放 | KDE 配置为只读；请在本机系统设置中调整 |
| 关闭被控端显示屏 | Plasma 6.8 / KWin 6.8 实测通过：关屏、取消关屏、保持关屏重连，以及远程画面和键鼠操作 |
| UU 超级屏（Windows 虚拟显示器） | 不支持；请共享现有物理显示器 |
| 登录界面或无人登录时的远控 | 不支持；需要先进入 Plasma Wayland 桌面 |
| 本机连接其他 UU 设备 | 支持；打开 UU 窗口期间本机暂停被控（2026-10-26 实机验证） |

KDE 服务会串流**所有已启用、未镜像、未旋转的物理显示器**（最多 8 块；主屏是 UU 中的第一块屏）。刷新率高于 144 Hz 的显示器按 144 Hz 上报；镜像或旋转的显示器不会串流，`uuway doctor` 会列出被略过的屏幕。UU 在 Wine 中使用的 Xvfb 用于内部运行；共享授权需要按提示逐块选择真实显示器。关屏模式使用单独授权的 KWin 虚拟屏，授权步骤和实现见 [KDE 关屏适配](docs/kde-virtual-display.md)。无显示器环境尚未验证，其他限制见 [Manjaro KDE 适配记录](docs/manjaro-kde.md)。

## 安装

准备 Manjaro/Arch **Plasma Wayland** 会话、支持 NVENC 的 NVIDIA 显卡及驱动、已启用的 multilib 仓库，以及自行从官方渠道取得的 UU 远程 **Windows 安装程序**。AUR 构建使用本机 pacman 的 CUDA 开发头文件；经过验证的测试机构建环境为 CUDA 13.3、系统 Wine 11.17。运行时另将经过哈希校验的 WineHQ **11.0** 放在 `/opt/uuway/wine-11.0`，不会替换系统 Wine：GPU 桥接依赖该版本的私有协议。构建需要下载 Wine 等源码/归档，安装后约占 1.5 GB。具体依赖与版本边界见 [AUR 文档](docs/aur-manjaro-kde.md)。

用 AUR 助手安装：

```bash
yay -S uuway-git
```

或手动构建：

```bash
git clone https://aur.archlinux.org/uuway-git.git
cd uuway-git
makepkg -si
```

随后在**被控机器已登录的 Plasma Wayland 桌面终端**中，以普通用户运行（不要给 `uuway setup` 加 `sudo`）：

```bash
uuway doctor
uuway setup --installer /path/to/UURemote_Setup.exe
uuway doctor
```

向导会要求你在 UU 窗口登录、按提示为每块显示器分别在 KDE 屏幕共享对话框中选择对应的屏幕并保存授权（选错的授权不会被保存，重新运行 `uuway setup --only portal` 即可再选），以及允许输入/剪贴板授权；系统输入规则可能需要管理员确认。安装包**不包含** UU 安装程序或你的账户数据。不要把另一台机器的 Wine 前缀、登录数据或 Portal 授权文件复制过来。

安装后可从应用菜单打开 **UUWay 控制台**，也可从 KDE 托盘启动、重启或停止本机远控；桌面登录时托盘会自动启动。使用 `uuway doctor` 查看本机状态，用 `systemctl --user status uu-native-bridge uu-native-text uu-native-display` 查看服务。AUR 升级由 pacman/AUR 助手完成，随后运行 `uuway refresh`；基于 Ubuntu `.deb`/`apt` 的 `uuway update install` 和 `rollback` **不适用于 Manjaro**。源码版的 `./install.sh` 同样不是 Manjaro 安装入口。

### 连接其他电脑

UU 每个 Wine 前缀只能打开一个窗口，而被控服务平时占用着它。需要从本机控制其他设备时，打开应用菜单中的 **UU 远程（控制其他电脑）**，或控制台概览页的「连接其他电脑」、托盘菜单的「连接其他电脑…」，也可以在终端运行 `uuway open`。UUWay 会暂停本机被控并打开 UU 窗口；用完后**从 UU 托盘图标退出**（关闭窗口只会最小化到托盘），约 15 秒后自动恢复被控。期间手机等设备无法连接本机。

`uuway autologin on` 只处理上游使用的 **GDM**，不会替你配置 KDE 常见的 SDDM。如果需要重启后无人值守上线，请自行评估并配置桌面自动登录的安全风险；停在登录界面时 UUWay 不在线。

### 采集没有画面

屏幕共享授权成功不代表 PipeWire 已送出帧。测试机曾出现仅剩“虚拟输出”、采集无帧的情况；重启 WirePlumber 后声音设备与采集均恢复。**这会中断当前媒体连接**，确认可接受时再执行：

```bash
systemctl --user restart wireplumber.service
uuway setup --only portal --force portal
```

再次授权时仍需按提示逐块选择物理屏幕。排错步骤见 [AUR 文档](docs/aur-manjaro-kde.md)。

## 原理与项目来源

UUWay 让 UU 的官方 Windows 被控端继续处理账号、连接与码率协商，同时把桌面画面、编码和输入接到 Linux 原生组件。此 fork 为 Plasma Wayland 增加了 KDE 专用的只读显示模式、原生 AUR 构建与 KDE 托盘适配。更详细的接口与实现见 [设计说明](docs/design.md)和[版本审计](docs/releases/4.42.0.2770-native-review.md)。

上游项目：[GaryOAO/UUWay](https://github.com/GaryOAO/UUWay)；更早的设计源自 Lachlan Chen 的 [uu-remote-ubuntu-bridge](https://github.com/lachlanchen/uu-remote-ubuntu-bridge)。感谢原作者及 Wine、DXVK、PipeWire 等项目。Ubuntu/GNOME 用户应查阅上游文档，**不要**把上游 `.deb` 当作本 fork 的 Manjaro 安装包。

本仓库的主项目许可证见 [LICENSE](LICENSE)（AGPL-3.0）；随包使用的第三方组件保留各自许可证。本项目与网易无关，不分发 UU 官方程序文件。
