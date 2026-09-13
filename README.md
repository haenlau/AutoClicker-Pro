<div align="center">

# AutoClicker Pro 🖱️

**Windows 桌面鼠标自动化工具 —— 自动连点 + 宏录制回放，内置拟人化随机行为**

**Windows desktop mouse automation — auto-clicker + macro record & replay, with humanized randomness**

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)
![Release](https://img.shields.io/github/v/release/haenlau/AutoClicker-Pro)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

**[简体中文](#zh) | [English](#en)**

</div>

<a id="zh"></a>

## 简介

AutoClicker Pro 是一个免安装的 Windows 桌面工具，把重复的鼠标操作交给程序：它既能按你设定的节奏自动连点，也能把你的一次完整操作录制成宏、精确回放。所有随机化（间隔抖动、位置偏移、偶尔停顿）都是为了模拟真人的操作节奏，而不是机械的固定周期。

## 功能特性

- **自动连点 · 三种坐标模式**
  - **跟随鼠标** —— 鼠标移到哪，点到哪
  - **固定坐标** —— 3 秒倒计时拾取屏幕位置，连点期间你仍可切去其他窗口做事
  - **多点循环** —— 坐标列表按顺序轮流点击（可增删、可编辑、可滚动）
- **点击动作**：单击 / 双击（自动保持在系统双击时限内）/ 拖动（多点循环下为 A→B→C 连拖）
- **完整宏录制回放**：记录移动轨迹 + 按下/抬起事件（支持拖动、双击），绝对时间轴精确重放，不丢快速点击；可调速度倍率、间隔抖动、位置偏移、循环次数
- **拟人化防检测**：高斯分布的点击间隔、约 5% 概率插入 80–350ms"走神"停顿、落点高斯偏移、随机按下时长
- **脚本库**：录制内容可命名保存多个脚本，下拉即切换；配置导入/导出（含脚本），换电脑一键还原
- **系统托盘**：关闭即最小化到托盘，托盘菜单控制一切，托盘退出才是真正退出
- **全局热键**（任何窗口下有效）：`F6` 连点 · `F8` 录制 · `F9` 回放，触发自动跳转对应页面
- **紧急停止**：运行中把鼠标甩到屏幕左上角，所有动作立即停止——脚本跑飞时的保命开关
- **中英双语**（跟随系统语言，可切换）· **浅色/深色主题** · 设置自动持久化

## 下载

前往 [Releases](https://github.com/haenlau/AutoClicker-Pro/releases) 下载最新版 `AutoClicker.exe`（免安装，约 50MB，Windows 10/11 x64）。

## 快速上手

1. **选坐标模式**：跟随鼠标 / 固定坐标 / 多点循环
2. **设参数**：点击间隔、随机抖动、鼠标按键、点击动作；多点循环记得先"拾取添加"坐标
3. **`F6`** 启动连点，再按一次停止；想更拟人就打开"拟人模式"
4. **`F8`** 开始录制宏，正常操作鼠标，再按 `F8` 结束；**`F9`** 回放
5. **紧急情况**：把鼠标快速甩到屏幕左上角，一切动作立即停止

| 热键 | 功能 |
| --- | --- |
| `F6` | 开始 / 停止连点 |
| `F8` | 开始 / 停止录制 |
| `F9` | 开始 / 停止回放 |
| 甩到左上角 | 紧急停止一切动作 |

**常见提示**

- 录不到某些窗口的点击？目标程序若以**管理员身份**运行，本程序也需要以管理员身份运行才能收到输入事件
- 回放的双击被拆散成两次单击？本程序已自动识别"双击对"并保护；若仍异常，把"位置偏移"调小（≤3px）
- 杀毒软件报毒？PyInstaller 单文件程序偶发误报，加入白名单即可，介意者可从源码自行构建
- 部分游戏使用驱动级输入检测，`SendInput` 无法生效，模拟器窗口一般正常

## 从源码构建

```bash
pip install PySide6 pynput pillow pyinstaller

# 开发运行
python clicker.py

# 打包单文件 exe
pyinstaller --noconfirm --onefile --windowed --clean \
  --icon=icon.ico --add-data "icon.ico;." \
  --name=AutoClicker clicker.py
```

测试（无头运行，45 项功能回归）：

```bash
AC_TEST=1 PYTHONUNBUFFERED=1 python tests/full_test.py
```

## 项目结构

```
clicker.py            全部源码（单文件）
tests/full_test.py    全量功能回归测试（45 项断言，offscreen 无头运行）
gen_icon.py           图标生成脚本
icon.ico / icon.png   应用图标
AutoClicker.spec      PyInstaller 打包配置
HANDOFF.md            开发者交接文档（架构、线程模型、历史坑）
```

## 免责声明

本工具仅供个人自动化使用，请勿用于破坏目标服务公平性的场景；用于游戏等平台时请自行遵守其用户条款，使用产生的一切后果由使用者自行承担。

## License

[MIT](LICENSE)

---

<a id="en"></a>

## Introduction

AutoClicker Pro is a portable Windows desktop tool that hands repetitive mouse work over to a program: it can auto-click at a pace you define, and it can record a full sequence of your actions as a macro and replay it precisely. All the randomness built in (interval jitter, position offset, occasional pauses) exists to mimic real human rhythm instead of a mechanical fixed cycle.

## Features

- **Auto-clicking · three coordinate modes**
  - **Follow mouse** — clicks wherever the cursor is
  - **Fixed position** — pick a spot with a 3-second countdown; you can keep working in other windows while it clicks
  - **Multi-point loop** — cycles through a coordinate list in order (add/remove/edit rows, scrollable)
- **Click actions**: single / double (gap kept within the system double-click limit) / drag (in multi-point mode, drags A→B→C through the list)
- **Full macro record & replay**: captures move paths + press/release events (drags and double-clicks included) and replays them on an absolute timeline without dropping fast clicks; adjustable speed, interval jitter, position offset and loop count
- **Humanized anti-detection**: Gaussian click intervals, ~5% chance of an 80–350 ms "distraction" pause, Gaussian landing-point offset, random press duration
- **Script library**: save multiple named recordings, switch via dropdown; export/import the full config (scripts included) to move to another PC
- **System tray**: closing minimizes to the tray where the menu controls everything; Quit in the tray really exits
- **Global hotkeys** (work over any window): `F6` click · `F8` record · `F9` replay — each jumps to its matching page
- **Emergency stop**: fling the mouse to the top-left corner to stop everything instantly — the safety switch when a script runs away
- **Bilingual UI** (follows system language, switchable) · **light/dark themes** · settings persist automatically

## Download

Grab the latest `AutoClicker.exe` from [Releases](https://github.com/haenlau/AutoClicker-Pro/releases) (portable, ~50 MB, Windows 10/11 x64).

## Quick Start

1. **Pick a coordinate mode**: follow mouse / fixed position / multi-point loop
2. **Set parameters**: interval, jitter, mouse button, click action; in multi-point mode, add coordinates first via "Pick & add"
3. **`F6`** starts clicking, press again to stop; enable "Humanize" for organic timing
4. **`F8`** starts recording — use the mouse normally, press `F8` again to finish; **`F9`** replays
5. **Emergency**: fling the mouse to the top-left corner to stop everything instantly

| Hotkey | Action |
| --- | --- |
| `F6` | Start / stop clicking |
| `F8` | Start / stop recording |
| `F9` | Start / stop replay |
| Fling to top-left corner | Emergency stop |

**Tips**

- Can't record clicks in some windows? If the target runs **as administrator**, this app must run as administrator too to receive its input events
- Replayed double-clicks split into two single clicks? "Double-click pairs" are detected and protected automatically; if it still happens, lower "Position offset" (≤3 px)
- Antivirus flags the exe? Occasional false positive for PyInstaller one-file builds — add an exclusion, or build from source yourself
- Some games use driver-level input checks that `SendInput` cannot pass; emulator windows normally work

## Build from Source

```bash
pip install PySide6 pynput pillow pyinstaller

# Run in development
python clicker.py

# Build a single-file exe
pyinstaller --noconfirm --onefile --windowed --clean \
  --icon=icon.ico --add-data "icon.ico;." \
  --name=AutoClicker clicker.py
```

Tests (headless, 45 functional regression checks):

```bash
AC_TEST=1 PYTHONUNBUFFERED=1 python tests/full_test.py
```

## Project Structure

```
clicker.py            All source code (single file)
tests/full_test.py    Full regression suite (45 assertions, headless)
gen_icon.py           Icon generator script
icon.ico / icon.png   App icons
AutoClicker.spec      PyInstaller build config
HANDOFF.md            Developer handoff doc (architecture, threading, pitfalls)
```

## Disclaimer

This tool is intended for personal automation only. Do not use it to undermine the fairness of a target service. When using it on games or other platforms, you are responsible for complying with their terms of service.

## License

[MIT](LICENSE)
