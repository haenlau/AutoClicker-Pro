# -*- coding: utf-8 -*-
"""
AutoClicker Pro — Windows 鼠标连点器 & 录制回放（PySide6 / Qt 版）v4.6
设计语言：Apple 液态玻璃 / macOS（中性灰阶、发丝线、抗锯齿圆角、药丸按钮、
按压/悬停反馈、语义色、动画开关与分段控制器）

- 连点：跟随鼠标 / 固定坐标（3秒拾取）/ 多点循环（坐标列表，支持单击/双击/拖动）
- 拟人化防检测：高斯间隔 + 5%走神停顿 + 高斯位置偏移 + 随机按下时长
- 录制：完整宏（移动轨迹+按下/抬起，支持拖动、双击），不丢快速点击
- 回放：平滑路径、绝对时间轴、双击对保护，速度/抖动/偏移/循环可调
- 脚本库（命名保存/下拉切换）、配置导入导出、系统托盘、紧急停止（甩角）
- 中英双语 + 浅色/深色主题 + 设置自动持久化
- 全局热键：F6=连点 F8=录制 F9=回放

线程模型：钩子/轮询线程只写数据结构，一切界面更新经 _ui_q 队列由
QTimer 在 GUI 线程统一执行。所有可中断等待用 sleep 轮询（勿改 Event.wait）。
"""
import ctypes
import json
import os
import queue
import random
import sys
import threading
import time

from PySide6.QtCore import (QTimer, Qt, QSize, QEasingCurve, QVariantAnimation,
                            QRectF, QPointF, Signal)
from PySide6.QtGui import QColor, QIcon, QPainter, QFont, QFontMetrics, QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                               QPushButton, QLineEdit, QFrame, QVBoxLayout,
                               QHBoxLayout, QGridLayout, QTabWidget, QTextEdit,
                               QMessageBox, QFileDialog, QGraphicsDropShadowEffect,
                               QScrollArea, QSystemTrayIcon, QMenu, QComboBox,
                               QInputDialog, QSizePolicy)

from pynput import mouse, keyboard

APP_NAME = "AutoClicker Pro"
CFG_VERSION = 4

# ---------------- i18n ----------------
TR = {
    "zh": {
        "app_title": "鼠标连点器 & 录制回放",
        "tab_clicker": "自动连点", "tab_record": "录制回放",
        "tab_settings": "设置", "tab_help": "帮助",
        "target": "目标位置", "timing": "点击节奏", "behavior": "点击方式",
        "pos_mode_follow": "跟随鼠标", "pos_mode_fixed": "固定坐标",
        "pos_mode_multi": "多点循环",
        "x": "X", "y": "Y", "pick_current": "◈  拾取位置 (3秒)",
        "pick_countdown": "移到目标… {n}", "pick_cancel": "取消拾取",
        "picking": "拾取中：请把鼠标移到目标位置 ({n} 秒后捕获)",
        "points_hint": "按列表顺序依次点击，循环往复",
        "pick_add": "◈ 拾取添加 (3秒)",
        "points_empty": "列表为空 — 点“拾取添加”或手动输入坐标",
        "theme_light": "浅色", "theme_dark": "深色", "appearance": "外观",
        "interval": "点击间隔", "jitter": "随机抖动",
        "human": "拟人模式", "human_sub": "高斯分布随机 + 偶尔走神停顿，防统计检测",
        "pos_jitter": "位置偏移", "pos_jitter_unit": "px", "mouse_button": "鼠标按键",
        "left": "左", "right": "右", "loops": "循环次数", "loops_unit": "次  ·  0 = 无限",
        "start": "开始连点 · F6", "stop_click": "停止连点 · F6",
        "record": "●  录制 · F8", "stop_rec": "■  停止录制 · F8",
        "play": "▶  回放 · F9", "stop_play": "■  停止回放 · F9",
        "clear": "清空", "save_script": "导出脚本", "load_script": "导入脚本",
        "export_cfg": "⭳  导出配置", "import_cfg": "⭱  导入配置",
        "rec_card": "录制状态", "play_card": "回放设置",
        "speed": "速度倍率", "rec_jitter": "间隔抖动", "rec_jitter_unit": "ms",
        "rec_pos_jitter": "位置偏移", "rec_pos_jitter_unit": "px",
        "rec_loops": "循环次数", "rec_loops_unit": "次", "rec_human": "拟人模式",
        "rec_none": "尚未录制 — 按 F8 开始，移动轨迹与按下抬起都会记录",
        "rec_ok": "坐标自检正常", "rec_bad": "坐标自检偏差约 {n}px",
        "rec_info_fmt": "{c} 次点击 · {m} 个移动点 · {check}",
        "general": "通用", "cfg_card": "配置管理", "cfg_note": "设置自动保存到本机。导出的配置包含全部参数与录制脚本，可在其他电脑导入还原。",
        "auto_load": "启动时恢复上次设置", "about": "关于",
        "language": "界面语言",
        "corner_stop": "紧急停止", "corner_sub": "鼠标甩到屏幕左上角，立即停止全部动作",
        "corner_stopped": "已紧急停止（鼠标移到屏幕角落）",
        "close_to_tray": "关闭时最小化到托盘",
        "tray_show": "显示主窗口", "tray_quit": "退出",
        "tray_note": "已最小化到托盘 · F6/F8/F9 热键仍可用",
        "menu_click": "连点 · F6", "menu_stop_click": "停止连点 · F6",
        "menu_rec": "录制 · F8", "menu_stop_rec": "停止录制 · F8",
        "menu_play": "回放 · F9", "menu_stop_play": "停止回放 · F9",
        "click_action": "点击动作",
        "action_single": "单击", "action_double": "双击", "action_drag": "拖动",
        "script_lib": "脚本库", "lib_save": "保存", "lib_del": "删除",
        "lib_name": "脚本名称", "lib_default": "脚本",
        "lib_confirm": "确定删除脚本“%s”？",
        "lib_saved": "已保存脚本“%s”", "lib_loaded": "已加载脚本“%s”",
        "lib_deleted": "已删除脚本“%s”", "lib_nothing": "当前没有录制内容可保存",
        "state_idle": "空闲", "state_click": "连点中", "state_rec": "录制中", "state_play": "回放中",
        "status_ready": "就绪",
        "pick_ok": "已捕获当前鼠标坐标 ({x}, {y})",
        "clicking": "连点中… 已点击 {n} 次", "click_done": "连点结束，共 {n} 次",
        "recording": "录制中… (F8 停止)",
        "rec_done": "录制结束：{c} 次点击，{m} 个移动点",
        "playing": "回放中… 第 {l} 轮 · {n} 步", "play_done": "回放结束，共执行 {n} 步",
        "cleared": "已清空录制", "saved_to": "脚本已保存: {p}", "loaded_from": "脚本已加载: {p}",
        "cfg_saved": "配置已导出: {p}", "cfg_loaded": "配置已导入: {p}",
        "need_stop_play": "回放进行中，无法录制。请先按 F9 停止回放。",
        "need_stop_rec": "录制进行中，无法回放。请先按 F8 停止录制。",
        "need_record": "还没有录制内容，请先按 F8 录制。",
        "need_stop_save": "录制进行中，请先停止再保存。",
        "nothing_saved": "没有可保存的录制内容。",
        "nothing_loaded": "请先停止录制/回放再加载。",
        "load_fail": "加载失败", "cfg_fail": "配置导入失败",
        "invalid_cfg": "这不是本程序的配置文件。",
        "preview_fmt": "平均每 {i} 点一次 · 实际间隔 {lo} ~ {hi} 随机（{mode}）",
        "mode_gauss": "高斯分布", "mode_uniform": "均匀随机",
        "tip_interval": "两次点击的平均等待时间。单位选 s 可直接填秒，如 5 = 每 5 秒一次。",
        "tip_jitter": "每次间隔的随机幅度。拟人模式下按高斯散开，并有 5% 概率走神停顿。",
        "tip_posj": "落点在目标坐标周围随机偏移的最大像素，拟人模式下中心密集边缘稀疏。",
        "tip_human": "频率与位置高斯随机化，打破固定周期，防止被统计方式识别为机器。",
        "tip_speed": "大于 1 加快回放，小于 1 放慢。",
        "help_title": "使用帮助",
    },
    "en": {
        "app_title": "Mouse Auto Clicker & Macro",
        "tab_clicker": "Auto Clicker", "tab_record": "Record & Replay",
        "tab_settings": "Settings", "tab_help": "Help",
        "target": "Target Position", "timing": "Click Timing", "behavior": "Click Behavior",
        "pos_mode_follow": "Follow mouse", "pos_mode_fixed": "Fixed position",
        "pos_mode_multi": "Multi-point",
        "x": "X", "y": "Y", "pick_current": "◈  Pick position (3s)",
        "pick_countdown": "Move to target… {n}", "pick_cancel": "Cancel pick",
        "picking": "Picking: move the mouse to the target ({n}s)",
        "points_hint": "Clicks the points in order, cycling forever",
        "pick_add": "◈ Pick & add (3s)",
        "points_empty": "List is empty — pick or type coordinates",
        "theme_light": "Light", "theme_dark": "Dark", "appearance": "Appearance",
        "interval": "Interval", "jitter": "Jitter",
        "human": "Humanize", "human_sub": "Gaussian randomness + occasional pauses, resists detection",
        "pos_jitter": "Position offset", "pos_jitter_unit": "px", "mouse_button": "Button",
        "left": "L", "right": "R", "loops": "Loops", "loops_unit": "·  0 = infinite",
        "start": "Start Clicking · F6", "stop_click": "Stop Clicking · F6",
        "record": "●  Record · F8", "stop_rec": "■  Stop Recording · F8",
        "play": "▶  Replay · F9", "stop_play": "■  Stop Replay · F9",
        "clear": "Clear", "save_script": "Export Script", "load_script": "Import Script",
        "export_cfg": "⭳  Export Config", "import_cfg": "⭱  Import Config",
        "rec_card": "Recording", "play_card": "Playback Settings",
        "speed": "Speed", "rec_jitter": "Interval jitter", "rec_jitter_unit": "ms",
        "rec_pos_jitter": "Position offset", "rec_pos_jitter_unit": "px",
        "rec_loops": "Loops", "rec_loops_unit": "", "rec_human": "Humanize",
        "rec_none": "Nothing recorded — press F8; moves and press/release are captured",
        "rec_ok": "coord check OK", "rec_bad": "coord check ~{n}px off",
        "rec_info_fmt": "{c} clicks · {m} move points · {check}",
        "general": "General", "cfg_card": "Configuration", "cfg_note": "Settings persist automatically. Exported config contains all parameters and the recorded script — import it on another PC.",
        "auto_load": "Restore last settings on startup", "about": "About",
        "language": "Language",
        "corner_stop": "Emergency stop", "corner_sub": "Fling mouse to the top-left corner to stop everything",
        "corner_stopped": "Emergency-stopped (mouse at screen corner)",
        "close_to_tray": "Close to tray",
        "tray_show": "Show Window", "tray_quit": "Quit",
        "tray_note": "Hidden to tray · hotkeys F6/F8/F9 still work",
        "menu_click": "Clicking · F6", "menu_stop_click": "Stop Clicking · F6",
        "menu_rec": "Record · F8", "menu_stop_rec": "Stop Recording · F8",
        "menu_play": "Replay · F9", "menu_stop_play": "Stop Replay · F9",
        "click_action": "Click Action",
        "action_single": "Single", "action_double": "Double", "action_drag": "Drag",
        "script_lib": "Script Library", "lib_save": "Save", "lib_del": "Delete",
        "lib_name": "Script name", "lib_default": "Script",
        "lib_confirm": 'Delete script "%s"?',
        "lib_saved": 'Saved script "%s"', "lib_loaded": 'Loaded script "%s"',
        "lib_deleted": 'Deleted script "%s"', "lib_nothing": "Nothing recorded to save",
        "state_idle": "Idle", "state_click": "Clicking", "state_rec": "Recording", "state_play": "Replaying",
        "status_ready": "Ready",
        "pick_ok": "Captured current mouse position ({x}, {y})",
        "clicking": "Clicking… {n} clicks", "click_done": "Clicking finished, {n} total",
        "recording": "Recording… (F8 to stop)",
        "rec_done": "Recording done: {c} clicks, {m} move points",
        "playing": "Replaying… lap {l} · {n} steps", "play_done": "Replay finished, {n} steps",
        "cleared": "Recording cleared", "saved_to": "Script saved: {p}", "loaded_from": "Script loaded: {p}",
        "cfg_saved": "Config exported: {p}", "cfg_loaded": "Config imported: {p}",
        "need_stop_play": "Replay is running. Press F9 to stop it first.",
        "need_stop_rec": "Recording is running. Press F8 to stop it first.",
        "need_record": "Nothing recorded yet. Press F8 to record first.",
        "need_stop_save": "Recording is running. Stop it before saving.",
        "nothing_saved": "Nothing to save.",
        "nothing_loaded": "Stop recording/replay before loading.",
        "load_fail": "Load failed", "cfg_fail": "Config import failed",
        "invalid_cfg": "This is not a config file of this app.",
        "preview_fmt": "One click every {i} on average · interval random in {lo} ~ {hi} ({mode})",
        "mode_gauss": "Gaussian", "mode_uniform": "uniform",
        "tip_interval": "Average wait between clicks. Pick 's' to type seconds, e.g. 5 = every 5 s.",
        "tip_jitter": "Random range of each interval. Gaussian in humanize mode with 5% micro-pauses.",
        "tip_posj": "Max pixel offset around the target. Gaussian: dense center, sparse edges.",
        "tip_human": "Gaussian-randomizes timing and position to break fixed patterns and resist statistical detection.",
        "tip_speed": "> 1 speeds replay up, < 1 slows it down.",
        "help_title": "Help",
    },
}

HELP_TEXT = {
    "zh": '【快速上手】\n\n◆ 自动连点（三种模式）\n  · 跟随鼠标：鼠标移到哪点到哪。按 F6 开始，再按 F6 停止。\n  · 固定坐标：点“拾取位置 (3秒)”，在倒计时内把鼠标移到目标处自动捕获坐标；\n    之后按 F6 即在该点连点，期间可以切去其他窗口做事（不要遮挡目标位置）。\n  · 多点循环：把多个坐标加入列表（“拾取添加”倒计时捕获，或手动输入，\n    列表最多显示 3 行，更多可滚动，每行可编辑、可删除），连点按顺序轮流循环。\n  · 间隔与抖动单位互相独立，都可选 ms 或 s，例如“每 5 秒 ± 100ms”。\n  · 循环次数填 0 表示无限。\n\n◆ 录制回放\n  按 F8 开始录制，正常操作即可——移动轨迹、按下/抬起、双击、拖动、每次\n  操作的实际间隔都会被记录；再按 F8 结束。按 F9 回放，可调速度倍率、\n  间隔抖动、位置偏移、循环次数。录制内容可“导出脚本/导入脚本”反复使用。\n\n◆ 拟人化防检测\n  开启后：间隔按高斯分布随机（中心密集、偶尔偏快偏慢）；每次点击约 5% 概率\n  插入 80–350ms“走神”停顿；落点按高斯分布偏移；按下时长随机。固定周期是\n  最容易被统计方式识别的机器特征，建议始终保持开启。回放的“双击对”会被\n  自动识别保护：两次点击共用偏移、间隔保持在系统双击时限内。\n\n◆ 点击动作（连点扩展）\n  “点击方式”里可选：单击（默认）、双击（同一位置快速两击，间隔自动保持在\n  系统双击时限内）、拖动（按住→平滑移动→松开；多点循环模式下会从上一个\n  坐标拖到下一个坐标，即 A 拖到 B、B 拖到 C 循环）。\n\n◆ 脚本库\n  录制回放页可把当前录制“保存”为命名脚本，下拉框切换后“加载”或“删除”。\n  脚本库自动保存在本机，配合导出/导入配置可以迁移到其他电脑。\n\n◆ 托盘与紧急停止\n  点窗口关闭会最小化到系统托盘（托盘右键菜单可开始/停止/退出，可在设置里\n  关闭此行为）。开启“紧急停止”后，连点/回放/录制运行中把鼠标快速甩到屏幕\n  左上角，所有动作立即停止并弹出通知——脚本跑飞时的保命开关。\n\n◆ 全局热键（任何窗口下有效）\n  F6 开始/停止连点 · F8 开始/停止录制 · F9 开始/停止回放\n  触发后会自动跳到对应页面显示状态。\n\n◆ 配置与外观\n  · 所有设置自动保存，下次打开原样恢复。\n  · “设置”页可导出/导入完整配置（含全部参数与录制脚本），换电脑一键还原。\n  · 顶栏 ☀/🌙 切换浅色/深色主题。\n\n【常见问题】\n\n· 连点时还能用鼠标干别的事吗？\n  “固定坐标”模式可以：自动点击注入到固定点，你的鼠标在其他窗口正常工作\n  （注意别让其他窗口挡住目标位置）。“跟随鼠标”“多点循环”和“回放”都会\n  占用鼠标，期间无法干别的。\n· 录不到某些窗口的点击？\n  目标程序若以管理员身份运行，普通权限的程序收不到它的输入事件。右键本软件\n  →“以管理员身份运行”再录制。\n· 通过远程桌面(RDP)连接无屏电脑使用？\n  本软件已声明 DPI 感知，坐标系自动统一。注意：录制和回放时保持 RDP 窗口\n  分辨率一致；录制期间保持会话连接。\n· 回放的双击变成两次单击？\n  本软件已自动识别“双击对”：回放时两次点击共用位置偏移、间隔保持在系统\n  双击时限内。若仍异常，把“位置偏移”调小（≤3px）。\n· 杀毒软件报毒？\n  PyInstaller 打包的单文件程序偶发误报，加入白名单即可。\n· 点击无效？\n  某些游戏/应用使用驱动级输入检测，SendInput 无法生效；模拟器窗口一般正常。\n  请勿最小化目标窗口。\n',
    "en": '[Quick Start]\n\n◆ Auto Clicking (three modes)\n  · Follow mouse: clicks wherever the mouse is. F6 to start, F6 to stop.\n  · Fixed position: click "Pick position (3s)", move the mouse to the target\n    within the countdown — the position is captured automatically. Then F6\n    clicks that point while you work in other windows (don\'t cover it).\n  · Multi-point: add coordinates to the list ("Pick & add" countdown or type\n    them; up to 3 rows visible, scroll for more; editable, deletable) —\n    clicking cycles through the list in order.\n  · Interval and jitter each have their own ms/s unit, e.g. "every 5s ± 100ms".\n  · Loops = 0 means infinite.\n\n◆ Record & Replay\n  Press F8 to record — move paths, press/release, double-clicks, drags and the\n  real timing of every action are captured; F8 again to finish. F9 replays with\n  speed, interval jitter, position offset and loops. Export/Import scripts to\n  reuse recordings.\n\n◆ Humanized anti-detection\n  When on: intervals follow a Gaussian distribution (dense near center,\n  occasionally faster/slower); each click has ~5% chance of an 80–350ms\n  micro-pause; landing points are Gaussian-offset; press duration is random.\n  Fixed periods are the easiest machine signature to detect statistically —\n  keep it on. Replayed "double-click pairs" are protected automatically:\n  both clicks share one offset and the gap stays within the system limit.\n\n◆ Click Action (extensions)\n  In "Click Behavior" choose: Single (default), Double (two fast clicks at the\n  same point, gap kept within the system double-click limit), Drag (press →\n  smooth move → release; in Multi-point mode it drags from one coordinate to\n  the next — A to B, then B to C, cycling).\n\n◆ Script Library\n  Save the current recording as a named script, switch via the dropdown, then\n  Load or Delete. The library persists locally; use config export/import to\n  move everything to another PC.\n\n◆ Tray & Emergency Stop\n  Closing the window minimizes to the system tray (right-click the tray icon\n  for start/stop/quit; can be disabled in Settings). With "Emergency stop" on,\n  flinging the mouse to the top-left corner while running instantly stops\n  clicking/replay/recording and shows a notification — the safety switch when\n  a script runs away.\n\n◆ Global Hotkeys (work over any window)\n  F6 click · F8 record · F9 replay\n  Triggering a hotkey switches to the matching tab so status is visible.\n\n◆ Config & Appearance\n  · All settings persist automatically.\n  · Export/Import the full config (all parameters + recorded script) in\n    Settings to move to another PC.\n  · ☀/🌙 in the header switches light/dark theme.\n\n[FAQ]\n\n· Can I use the mouse for other things while auto-clicking?\n  "Fixed position" mode: yes — clicks are injected at the fixed point while you\n  work in other windows (don\'t cover the target). "Follow mouse", "Multi-point"\n  and Replay occupy the mouse, so no.\n· Some windows can\'t be recorded?\n  If the target app runs as administrator, a normal-privilege app cannot receive\n  its input. Right-click this app → "Run as administrator", then record.\n· Using a headless PC via RDP?\n  This app is DPI-aware, so coordinate systems unify automatically. Keep the RDP\n  window resolution the same between recording and replay; stay connected while\n  recording.\n· Replayed double-clicks become two single clicks?\n  Double-click pairs are detected automatically: both clicks share one position\n  offset and the gap stays within the system double-click time. If it still\n  fails, reduce "Position offset" to <= 3 px.\n· Antivirus flags the exe?\n  Occasional false positive for PyInstaller one-file builds — add an exclusion.\n· Clicks have no effect?\n  Some games/apps use driver-level input checks that SendInput cannot pass.\n  Emulator windows normally work. Do not minimize the target window.\n',
}


# ---------------- Win32 SendInput ----------------
user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", _INPUTUNION)]


def apply_window_chrome(hwnd, hexcolor="#F2F3F7"):
    """Win11：原生圆角窗口 + 标题栏/边框融入界面底色。"""
    try:
        dwm = ctypes.WinDLL("dwmapi")
        r, g, b = int(hexcolor[1:3], 16), int(hexcolor[3:5], 16), int(hexcolor[5:7], 16)
        colorref = ctypes.c_uint((b << 16) | (g << 8) | r)
        dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 33, ctypes.byref(ctypes.c_uint(2)), 4)
        dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 35, ctypes.byref(colorref), 4)
        dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 34, ctypes.byref(colorref), 4)
    except Exception:
        pass


def virtual_screen():
    return (user32.GetSystemMetrics(76), user32.GetSystemMetrics(77),
            user32.GetSystemMetrics(78), user32.GetSystemMetrics(79))


def cursor_pos():
    import ctypes.wintypes as wt
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def send_move(x, y):
    vx, vy, vw, vh = virtual_screen()
    nx = int((x - vx) * 65535 / max(vw - 1, 1))
    ny = int((y - vy) * 65535 / max(vh - 1, 1))
    mi = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
    inp = INPUT(INPUT_MOUSE, _INPUTUNION(mi))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_button(button, down):
    flag = {"left": MOUSEEVENTF_LEFTDOWN, "right": MOUSEEVENTF_RIGHTDOWN} if down \
        else {"left": MOUSEEVENTF_LEFTUP, "right": MOUSEEVENTF_RIGHTUP}
    mi = MOUSEINPUT(0, 0, 0, flag[button], 0, None)
    inp = INPUT(INPUT_MOUSE, _INPUTUNION(mi))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def do_click(x, y, button="left"):
    send_move(x, y)
    time.sleep(0.01)
    send_button(button, True)
    time.sleep(random.uniform(0.015, 0.045))
    send_button(button, False)


def replay_move(x, y, stop_evt, step=20, pause=0.004):
    cx, cy = cursor_pos()
    dist = max(abs(x - cx), abs(y - cy))
    steps = min(int(dist // step), 40)
    if steps < 1:
        send_move(x, y)
        return
    for i in range(1, steps + 1):
        if stop_evt.is_set():
            return
        send_move(int(cx + (x - cx) * i / steps), int(cy + (y - cy) * i / steps))
        time.sleep(pause)


# ---------------- 拟人化随机 ----------------

def _jitter_bonus_ms(jitter, human):
    if jitter <= 0:
        return 0.0
    if human:
        val = random.gauss(0, jitter / 2.0)
        val = min(max(val, -jitter), jitter)
        if random.random() < 0.05:
            val += random.uniform(80, 350)
        return val
    return random.uniform(-jitter, jitter)


def human_interval_ms(interval, jitter, human):
    return max(0.005, (interval + _jitter_bonus_ms(jitter, human)) / 1000.0)


def human_offset(radius, human):
    if radius <= 0:
        return 0, 0
    if human:
        dx = min(max(random.gauss(0, radius / 2.0), -radius), radius)
        dy = min(max(random.gauss(0, radius / 2.0), -radius), radius)
        return int(round(dx)), int(round(dy))
    return random.randint(-radius, radius), random.randint(-radius, radius)


def detect_double_clicks(events):
    """按系统双击参数识别双击对。返回 (pairs, spans)。"""
    dct = user32.GetDoubleClickTime() / 1000.0 + 0.05
    rect = max(user32.GetSystemMetrics(36), user32.GetSystemMetrics(37), 4)
    pairs = {}
    spans = set()
    pending = None
    for i, ev in enumerate(events):
        typ = ev.get("type", "click")
        if typ in ("down", "click"):
            if (pending and not pending[2]
                    and ev.get("button", "left") == pending[1].get("button", "left")
                    and 0 < ev["t"] - pending[1]["t"] <= dct
                    and abs(ev["x"] - pending[1]["x"]) <= rect
                    and abs(ev["y"] - pending[1]["y"]) <= rect):
                pairs[i] = pending[0]
                spans.update(range(pending[0] + 1, i + 2))
            pending = (i, ev, typ == "down")
        elif typ == "up":
            if pending and pending[2]:
                pending = (pending[0], pending[1], False)
    return pairs, spans


# ---------------- 配置 ----------------

def config_file(name="autoclicker_config.json"):
    for base in ([os.path.dirname(sys.executable)] if getattr(sys, "frozen", False) else []) \
            + [os.path.dirname(os.path.abspath(__file__)),
               os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)]:
        try:
            p = os.path.join(base, name)
            with open(p, "a", encoding="utf-8"):
                pass
            return p
        except OSError:
            continue
    return os.path.join(os.path.expanduser("~"), name)


def resource_path(name):
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def default_lang():
    try:
        if (user32.GetUserDefaultUILanguage() & 0xFF) == 0x04:
            return "zh"
    except Exception:
        pass
    return "en"


# ---------------- 简易响应变量 ----------------

class Var:
    """最小可观察变量：界面控件与逻辑共享。"""

    def __init__(self, value):
        self._v = value
        self._cbs = []

    def get(self):
        return self._v

    def set(self, v):
        if v == self._v:
            return
        self._v = v
        for cb in list(self._cbs):
            try:
                cb(v)
            except Exception:
                pass

    def connect(self, cb):
        self._cbs.append(cb)


# ---------------- 主题 ----------------

THEMES = {
    "light": {
        "BG": "#F2F3F7", "CARD": "#FFFFFF", "HAIR": "#E5E7EC",
        "TEXT": "#1D1D1F", "MUTED": "#85858B",
        "TRACK": "#ECECEF", "FIELD": "#F1F2F4",
        "PRIMARY": "#3A3A3C", "PRIMARY_H": "#4B4B4E", "PRIMARY_P": "#2C2C2E",
        "SECOND": "#FFFFFF", "SECOND_H": "#F3F4F7", "SECOND_P": "#E8EAEE",
        "SW_OFF": "#E9E9EA", "KNOB": "#FFFFFF", "SEG_OUT": "#E5E7EC",
        "TOOLTIP_BG": "#1D1D1F", "TOOLTIP_FG": "#F5F5F7",
    },
    "dark": {
        "BG": "#1E1F24", "CARD": "#2A2B31", "HAIR": "#3A3B42",
        "TEXT": "#F2F2F5", "MUTED": "#9A9AA3",
        "TRACK": "#3A3B42", "FIELD": "#33343B",
        "PRIMARY": "#55565C", "PRIMARY_H": "#63646A", "PRIMARY_P": "#46474D",
        "SECOND": "#33343B", "SECOND_H": "#3D3E45", "SECOND_P": "#46474D",
        "SW_OFF": "#46474D", "KNOB": "#E8E8EC", "SEG_OUT": "#46474D",
        "TOOLTIP_BG": "#F2F2F5", "TOOLTIP_FG": "#1D1D1F",
    },
}
CUR = dict(THEMES["light"])

GREEN = "#34C759"
RED = "#FF453A"
ORANGE = "#FF9500"


def make_qss(t):
    return f"""
QWidget {{
  background: {t['BG']};
  color: {t['TEXT']};
  font-family: "Microsoft YaHei", "Segoe UI";
  font-size: 13px;
}}
QLabel {{ background: transparent; }}
#header {{ background: {t['CARD']}; border: 1px solid {t['HAIR']}; border-radius: 14px; }}
#titleLabel {{ font-size: 16px; font-weight: 600; background: transparent; color: {t['TEXT']}; }}
#caption {{ color: {t['MUTED']}; font-size: 12px; background: transparent; }}
#card {{ background: {t['CARD']}; border: 1px solid {t['HAIR']}; border-radius: 16px; }}
#cardTitle {{ font-weight: 600; color: {t['TEXT']}; background: transparent; }}
#muted {{ color: {t['MUTED']}; font-size: 12px; background: transparent; }}
#rowSep {{ background: {t['HAIR']}; max-height: 1px; border: none; }}
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
  background: transparent; color: {t['MUTED']};
  padding: 7px 16px; font-weight: 600; border: none;
  border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {t['TEXT']}; border-bottom: 2px solid {t['PRIMARY']}; }}
QTabBar::tab:hover:!selected {{ color: {t['TEXT']}; }}
QPushButton[kind="primary"] {{
  background: {t['PRIMARY']}; color: {t['KNOB']}; border: none;
  border-radius: 16px; padding: 0 18px; min-height: 32px; font-weight: 600;
}}
QPushButton[kind="primary"]:hover {{ background: {t['PRIMARY_H']}; }}
QPushButton[kind="primary"]:pressed {{ background: {t['PRIMARY_P']}; }}
QPushButton[kind="danger"] {{
  background: {RED}; color: #FFFFFF; border: none;
  border-radius: 16px; padding: 0 18px; min-height: 32px; font-weight: 600;
}}
QPushButton[kind="danger"]:hover {{ background: #E63E33; }}
QPushButton[kind="danger"]:pressed {{ background: #CC342B; }}
QPushButton[kind="secondary"] {{
  background: {t['SECOND']}; color: {t['TEXT']}; border: 1px solid {t['HAIR']};
  border-radius: 15px; padding: 0 14px; min-height: 30px;
}}
QPushButton[kind="secondary"]:hover {{ background: {t['SECOND_H']}; }}
QPushButton[kind="secondary"]:pressed {{ background: {t['SECOND_P']}; }}
QPushButton#hero {{
  background: {t['PRIMARY']}; color: {t['KNOB']}; border: none;
  border-radius: 20px; min-height: 40px; font-size: 14px; font-weight: 600;
}}
QPushButton#hero:hover {{ background: {t['PRIMARY_H']}; }}
QPushButton#hero:pressed {{ background: {t['PRIMARY_P']}; }}
QLineEdit {{
  background: {t['FIELD']}; border: 1px solid transparent;
  border-radius: 8px; padding: 5px 9px; font-size: 13px;
  selection-background-color: {t['PRIMARY']};
}}
QLineEdit:focus {{ background: {t['CARD']}; border: 1px solid {t['MUTED']}; }}
QToolTip {{
  background: {t['TOOLTIP_BG']}; color: {t['TOOLTIP_FG']}; border: none;
  border-radius: 8px; padding: 6px 9px; font-size: 12px;
}}
QTextEdit {{ background: {t['CARD']}; border: none; font-size: 13px; color: {t['TEXT']}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {t['MUTED']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QComboBox {{
  background: {t['FIELD']}; border: 1px solid transparent; border-radius: 8px;
  padding: 5px 10px; font-size: 13px; color: {t['TEXT']};
}}
QComboBox:focus {{ background: {t['CARD']}; border: 1px solid {t['MUTED']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
  background: {t['CARD']}; color: {t['TEXT']}; border: 1px solid {t['HAIR']};
  border-radius: 8px; selection-background-color: {t['SECOND_H']};
  selection-color: {t['TEXT']}; outline: none;
}}
QMenu {{
  background: {t['CARD']}; color: {t['TEXT']}; border: 1px solid {t['HAIR']};
  border-radius: 10px; padding: 4px;
}}
QMenu::item {{ padding: 6px 20px; border-radius: 7px; }}
QMenu::item:selected {{ background: {t['SECOND_H']}; }}
QMenu::separator {{ height: 1px; background: {t['HAIR']}; margin: 4px 8px; }}
QMessageBox {{ background: {t['CARD']}; }}
QMessageBox QLabel {{ color: {t['TEXT']}; font-size: 13px; background: transparent; }}
QMessageBox QPushButton {{
  background: {t['PRIMARY']}; color: {t['KNOB']}; border: none;
  border-radius: 14px; padding: 4px 12px; min-height: 26px; min-width: 76px;
  font-weight: 600;
}}
QMessageBox QPushButton:hover {{ background: {t['PRIMARY_H']}; }}
QInputDialog {{ background: {t['CARD']}; }}
QFileDialog {{ background: {t['CARD']}; }}
"""


def mix(c1, c2, t):
    return QColor(int(c1.red() + (c2.red() - c1.red()) * t),
                  int(c1.green() + (c2.green() - c1.green()) * t),
                  int(c1.blue() + (c2.blue() - c1.blue()) * t))


class Segmented(QWidget):
    """iOS 分段控制器：灰色轨道 + 白色滑块（滑动动画，抗锯齿）。"""
    changed = Signal(str)

    def __init__(self, options, var, on_change=None, height=30, font_pt=10,
                 pad=None, min_w=None, parent=None):
        super().__init__(parent)
        self.opts = options
        self.var = var
        self.cb = on_change
        self.font_pt = font_pt
        self.pad = pad if pad is not None else (24 if font_pt <= 9 else 34)
        self.min_w = min_w if min_w is not None else (46 if font_pt <= 9 else 58)
        self.setFixedHeight(height)
        self._pos = float(self._index_of(var.get()))
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fit()
        var.connect(self._sync)

    def _index_of(self, v):
        for i, (val, _) in enumerate(self.opts):
            if val == v:
                return i
        return 0

    def _sync(self, v):
        self._animate(self._index_of(v))
        self.update()

    def _animate(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(float(target))
        self._anim.start()

    def _on_anim(self, v):
        self._pos = float(v)
        self.update()

    def _fit(self):
        fm = QFontMetrics(QFont("Microsoft YaHei", self.font_pt))
        w = max(fm.horizontalAdvance(lbl) for _, lbl in self.opts) + self.pad
        self.setFixedWidth(max(w, self.min_w) * len(self.opts))

    def mousePressEvent(self, e):
        n = len(self.opts)
        idx = max(0, min(n - 1, int(e.position().x() / (self.width() / n))))
        val = self.opts[idx][0]
        if val != self.var.get():
            self.var.set(val)
            if self.cb:
                self.cb(val)
            self.changed.emit(val)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(CUR["TRACK"]))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), h / 2, h / 2)
        seg_w = w / len(self.opts)
        m = 2.0
        sx = m + self._pos * seg_w
        p.setBrush(QColor(CUR["KNOB"]))
        p.setPen(QColor(CUR["SEG_OUT"]))
        p.drawRoundedRect(QRectF(sx, m, seg_w - 2 * m, h - 2 * m),
                          (h - 2 * m) / 2, (h - 2 * m) / 2)
        p.setPen(Qt.PenStyle.NoPen)
        cur = self.var.get()
        fsel = QFont("Microsoft YaHei", self.font_pt, QFont.Weight.DemiBold)
        fnorm = QFont("Microsoft YaHei", self.font_pt)
        for i, (val, lbl) in enumerate(self.opts):
            # 滑块始终为浅色，选中文字固定用深色保证对比度
            p.setPen(QColor("#1D1D1F") if val == cur else QColor(CUR["MUTED"]))
            p.setFont(fsel if val == cur else fnorm)
            p.drawText(QRectF(i * seg_w, 0, seg_w, h), Qt.AlignmentFlag.AlignCenter, lbl)
        p.end()


class Switch(QWidget):
    """iOS 拨动开关：绿色轨道 + 白色圆钮，OutCubic 滑动动画。"""
    W, H = 42, 24

    def __init__(self, var, on_change=None, parent=None):
        super().__init__(parent)
        self.var = var
        self.cb = on_change
        self.setFixedSize(self.W, self.H)
        self._pos = 1.0 if var.get() else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        var.connect(self._sync)

    def _sync(self, _):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if self.var.get() else 0.0)
        self._anim.start()

    def _on_anim(self, v):
        self._pos = float(v)
        self.update()

    def mouseReleaseEvent(self, e):
        self.var.set(not self.var.get())
        if self.cb:
            self.cb()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.W, self.H
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix(QColor(CUR["SW_OFF"]), QColor(GREEN), self._pos))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        kx = h / 2 + self._pos * (w - h)
        p.setBrush(QColor(0, 0, 0, 28))
        p.drawEllipse(QPointF(kx, h / 2 + 1.6), h / 2 - 3.5, h / 2 - 3.5)
        p.setBrush(QColor(CUR["KNOB"]))
        p.drawEllipse(QPointF(kx, h / 2), h / 2 - 3.5, h / 2 - 3.5)
        p.end()


class Pill(QPushButton):
    """药丸按钮：kind = primary / secondary / danger，悬停与按压由 QSS 接管。"""

    def __init__(self, var, on_click=None, kind="primary", parent=None):
        super().__init__(var.get(), parent)
        self.var = var
        var.connect(self.setText)
        if on_click:
            self.clicked.connect(on_click)
        self.set_kind(kind)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_kind(self, kind):
        self.setProperty("kind", kind)
        self.style().unpolish(self)
        self.style().polish(self)


def card(title=None):
    """白色圆角玻璃卡片 + 柔和投影，返回 (frame, body_layout)。"""
    f = QFrame()
    f.setObjectName("card")
    shadow = QGraphicsDropShadowEffect(f)
    shadow.setBlurRadius(18)
    shadow.setXOffset(0)
    shadow.setYOffset(3)
    shadow.setColor(QColor(30, 32, 48, 26))
    f.setGraphicsEffect(shadow)
    v = QVBoxLayout(f)
    v.setContentsMargins(13, 10, 13, 11)
    v.setSpacing(5)
    if title:
        t = QLabel(title)
        t.setObjectName("cardTitle")
        v.addWidget(t)
    return f, v


def row(parent_layout):
    r = QHBoxLayout()
    r.setContentsMargins(0, 1, 0, 1)
    r.setSpacing(8)
    parent_layout.addLayout(r)
    return r


def sep(parent_layout):
    s = QFrame()
    s.setObjectName("rowSep")
    s.setFixedHeight(1)
    parent_layout.addWidget(s)


def caption(text):
    lbl = QLabel(text)
    lbl.setObjectName("muted")
    lbl.setWordWrap(True)
    return lbl


class PointsList(QWidget):
    """多点循环坐标列表：圆角容器内滚动（最多显示3行，超出用内部滚动条），
    新增行自动滚动到最新；与 V["points"] 双向同步。"""
    changed = Signal(list)

    MAX_H = 78    # 列表最大高度（恰好3行）

    def __init__(self, initial=None, hint_fn=None, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(
            f"QScrollArea{{background:{CUR['FIELD']};border:1px solid {CUR['HAIR']};"
            "border-radius:12px;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}")
        self.inner = QWidget()
        self.v = QVBoxLayout(self.inner)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(4)
        self.scroll.setWidget(self.inner)
        outer.addWidget(self.scroll)
        self.hint_fn = hint_fn
        self.hint = caption("")
        outer.addWidget(self.hint)
        self.rows = []
        self.rebuild(list(initial or []))

    def collect(self):
        pts = []
        for _, ex, ey in self.rows:
            try:
                x = int(float(ex.text()))
            except (ValueError, TypeError):
                x = 0
            try:
                y = int(float(ey.text()))
            except (ValueError, TypeError):
                y = 0
            pts.append([x, y])
        return pts

    def set_points(self, pts):
        pts = [list(p) for p in (pts or [])]
        if pts == self.collect():
            return
        self.rebuild(pts)

    def add_point(self, x=0, y=0):
        pts = self.collect()
        pts.append([int(x), int(y)])
        self.rebuild(pts)
        self.changed.emit(self.collect())

    def remove_row(self, idx):
        pts = self.collect()
        if 0 <= idx < len(pts):
            pts.pop(idx)
            self.rebuild(pts)
            self.changed.emit(self.collect())

    def rebuild(self, pts):
        for rw, _, _ in self.rows:
            rw.deleteLater()
        self.rows = []
        for p in pts:
            self._add_row(p[0], p[1])
        self._update_hint()
        self._fit_scroll_height()
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    def _fit_scroll_height(self):
        """列表容器高度：空=隐藏；不足3行=贴合内容；超过3行=封顶出滚动条。"""
        if not self.rows:
            self.scroll.setFixedHeight(0)
            self.scroll.setVisible(False)
            return
        self.scroll.setVisible(True)
        content = len(self.rows) * 22 + (len(self.rows) - 1) * 4 + 4
        self.scroll.setFixedHeight(min(content, self.MAX_H))

    def _add_row(self, x, y):
        rw = QWidget()
        rw.setStyleSheet("background: transparent;")   # 行透明，不遮容器底色
        h = QHBoxLayout(rw)
        h.setContentsMargins(6, 1, 2, 1)
        h.setSpacing(6)
        n = len(self.rows)
        idx = QLabel(f"{n + 1}.")
        idx.setObjectName("muted")
        field_qss = (f"QLineEdit{{background:{CUR['CARD']};border:1px solid {CUR['HAIR']};"
                     "border-radius:6px;padding:2px 7px;font-size:12px;}}")
        ex = QLineEdit(str(x))
        ex.setFixedWidth(80)
        ex.setFixedHeight(22)
        ex.setStyleSheet(field_qss)
        ey = QLineEdit(str(y))
        ey.setFixedWidth(80)
        ey.setFixedHeight(22)
        ey.setStyleSheet(field_qss)
        for e in (ex, ey):
            e.textChanged.connect(lambda *_: self.changed.emit(self.collect()))
        btn = QPushButton("✕")
        btn.setFixedSize(22, 22)
        btn.setProperty("kind", "secondary")
        btn.setStyleSheet("padding:0;min-height:0;font-size:10px;border-radius:7px;color:"
                          + CUR['MUTED'] + ";")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked=False, i=n: self.remove_row(i))
        h.addWidget(idx)
        h.addWidget(ex)
        h.addWidget(QLabel("Y"))
        h.addWidget(ey)
        h.addStretch(1)
        h.addWidget(btn)
        self.v.addWidget(rw)
        self.rows.append((rw, ex, ey))

    def _update_hint(self):
        self.hint.setText("" if self.rows else (self.hint_fn() or ""))
        self.hint.setVisible(not self.rows)   # 有坐标时整行隐藏，不留占位空白


# ---------------- 应用 ----------------


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(resource_path("icon.ico")))

        # 运行状态
        self.clicking = False
        self.recording = False
        self.playing = False
        self.clicker_stop = threading.Event()
        self.play_stop = threading.Event()
        self.recorded = []
        self.rec_start = 0.0
        self.mouse_listener = None
        self.kb_listener = None
        self._last_pos = (0, 0)
        self._coord_mismatch = 0
        self._rec_dirty = False
        self._ui_q = queue.Queue()
        self._quit = False
        self._corner_armed = True

        self.lang = default_lang()
        self.V = {}
        self._make_vars()
        self._load_persisted()
        self._wire_vars()
        self.library = {}
        self._lib_load_file()
        self._quit = False
        self._corner_armed = True

        # 主题：先于界面构建确定
        t = self.V["theme"].get()
        self.theme = t if t in THEMES else "light"
        CUR.clear()
        CUR.update(THEMES[self.theme])
        QApplication.instance().setStyleSheet(make_qss(CUR))

        self._build_central()
        self._start_coord_polling()
        self._start_hotkeys()
        self._create_tray()

        self._fit_window()
        self.pump = QTimer(self)
        self.pump.timeout.connect(self._pump)
        self.pump.start(80)
        QTimer.singleShot(120, lambda: apply_window_chrome(int(self.winId()), CUR["BG"]))

    # ---------- 变量 ----------
    def _make_vars(self):
        V = self.V
        V["pos_mode"] = Var("follow")
        V["pos_x"] = Var("0")
        V["pos_y"] = Var("0")
        V["interval"] = Var("200")
        V["unit"] = Var("ms")
        V["jitter"] = Var("50")
        V["jitter_unit"] = Var("ms")
        V["human"] = Var(True)
        V["pos_jitter"] = Var("5")
        V["button"] = Var("left")
        V["loops"] = Var("0")
        V["speed"] = Var("1.0")
        V["rec_jitter"] = Var("30")
        V["rec_pos_jitter"] = Var("5")
        V["rec_loops"] = Var("1")
        V["rec_human"] = Var(True)
        V["auto_load"] = Var(True)
        V["theme"] = Var("light")
        V["click_action"] = Var("single")
        V["corner_stop"] = Var(True)
        V["close_to_tray"] = Var(True)
        V["points"] = Var([])          # 多点循环：[[x, y], ...]
        self.var_live_coords = Var("")
        self.var_status = Var("")
        self.var_pill = Var("")
        self.var_rec_info = Var("")
        self.var_preview = Var("")
        self.var_btn_click = Var("")
        self.var_btn_rec = Var("")
        self.var_btn_play = Var("")

    def _wire_vars(self):
        for name in ("interval", "jitter", "unit", "jitter_unit", "human"):
            self.V[name].connect(lambda *_: self._update_preview())
        self._update_preview()

    def tr(self, key):
        return TR[self.lang].get(key, TR["en"].get(key, key))

    def _msg(self, text, error=False):
        """统一样式的对话框：居中文字 + 主题按钮。测试环境(AC_TEST)不进入模态循环。"""
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Icon.Critical if error else QMessageBox.Icon.NoIcon)
        box.setText(text)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.setDefaultButton(QMessageBox.StandardButton.Ok)
        try:
            lbl = box.findChild(QLabel)
            if lbl:
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
        if not os.environ.get("AC_TEST"):
            box.exec()

    def _settings_snapshot(self):
        return {k: v.get() for k, v in self.V.items()}

    def _apply_settings(self, data):
        for k, v in data.items():
            if k in self.V:
                self.V[k].set(v)

    # ---------- 持久化 ----------
    def _load_persisted(self):
        try:
            with open(config_file(), "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            return
        if data.get("app") != APP_NAME:
            return
        self.lang = data.get("language", self.lang)
        if self.V["auto_load"].get():
            self._apply_settings(data.get("settings", {}))

    def _save_persisted(self):
        try:
            with open(config_file(), "w", encoding="utf-8") as fp:
                json.dump({"app": APP_NAME, "version": CFG_VERSION,
                           "language": self.lang,
                           "settings": self._settings_snapshot()}, fp,
                          ensure_ascii=False, indent=1)
        except Exception:
            pass

    def _lib_load_file(self):
        try:
            with open(config_file("autoclicker_scripts.json"), "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                self.library = {k: v for k, v in data.items() if isinstance(v, list)}
        except Exception:
            self.library = {}

    def _lib_save_file(self):
        try:
            with open(config_file("autoclicker_scripts.json"), "w", encoding="utf-8") as fp:
                json.dump(self.library, fp, ensure_ascii=False, indent=1)
        except Exception:
            pass

    # ---------- 界面 ----------
    def _build_central(self):
        central = QWidget()
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        content = QWidget()
        content.setMaximumWidth(720)
        cl = QVBoxLayout(content)
        cl.setContentsMargins(10, 8, 10, 0)   # 顶栏作为圆角卡片悬浮，与下方卡片对齐
        cl.setSpacing(8)

        # 顶栏（独立圆角卡片）
        self.header = QFrame()
        self.header.setObjectName("header")
        hv = QHBoxLayout(self.header)
        hv.setContentsMargins(16, 8, 16, 8)
        hleft = QVBoxLayout()
        hleft.setSpacing(0)
        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        title.setMinimumWidth(1)
        self.coords_lbl = QLabel("")
        self.coords_lbl.setObjectName("caption")
        self.coords_lbl.setMinimumWidth(1)
        vx, vy, vw, vh = virtual_screen()
        self._res_text = f"{vw}×{vh}" + (f" ({vx},{vy})" if (vx, vy) != (0, 0) else "")
        hleft.addWidget(title)
        hleft.addWidget(self.coords_lbl)
        hv.addLayout(hleft)
        hv.addStretch(1)
        hv.addSpacing(12)
        self.lang_seg = Segmented([("zh", "中文"), ("en", "EN")],
                                  Var(self.lang),
                                  on_change=lambda v: self._switch_lang(v),
                                  height=24, font_pt=9)
        hv.addWidget(self.lang_seg)
        hv.addSpacing(8)
        self.theme_seg = Segmented([("light", "☀"), ("dark", "🌙")],
                                   Var(self.theme),
                                   on_change=lambda v: self._switch_theme(v),
                                   height=24, font_pt=10, pad=16, min_w=32)
        self.theme_seg.setToolTip(self.tr("appearance"))
        hv.addWidget(self.theme_seg)
        header_wrap = QWidget()
        hw = QVBoxLayout(header_wrap)
        hw.setContentsMargins(10, 0, 10, 0)
        hw.addWidget(self.header)
        cl.addWidget(header_wrap)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        cl.addWidget(self.tabs, 1)

        page_clicker = QWidget()
        w1 = QVBoxLayout(page_clicker)
        w1.setContentsMargins(10, 6, 10, 4)
        w1.setSpacing(7)
        self._build_clicker_tab(w1)
        self.tabs.addTab(page_clicker, "  " + self.tr("tab_clicker") + "  ")

        page_record = QWidget()
        w2 = QVBoxLayout(page_record)
        w2.setContentsMargins(10, 6, 10, 4)
        self._build_record_tab(w2)
        self.tabs.addTab(page_record, "  " + self.tr("tab_record") + "  ")

        page_settings = QWidget()
        w3 = QVBoxLayout(page_settings)
        w3.setContentsMargins(10, 6, 10, 4)
        self._build_settings_tab(w3)
        self.tabs.addTab(page_settings, "  " + self.tr("tab_settings") + "  ")

        page_help = QWidget()
        w4 = QVBoxLayout(page_help)
        w4.setContentsMargins(10, 6, 10, 4)
        self._build_help_tab(w4)
        self.tabs.addTab(page_help, "  " + self.tr("tab_help") + "  ")

        # 底栏
        status_wrap = QWidget()
        sw = QVBoxLayout(status_wrap)
        sw.setContentsMargins(10, 0, 10, 0)
        self.statusbar = QFrame()
        sb = QHBoxLayout(self.statusbar)
        sb.setContentsMargins(14, 2, 14, 10)
        self.state_lbl = QLabel("")
        self.state_lbl.setStyleSheet(
            f"background:{CUR['MUTED']};color:white;border-radius:9px;"
            "font-weight:600;font-size:12px;padding:3px 11px;")
        sb.addWidget(self.state_lbl)
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("caption")
        sb.addWidget(self.status_lbl)
        sb.addStretch(1)
        hk = QLabel("F6 · F8 · F9")
        hk.setObjectName("caption")
        sb.addWidget(hk)
        sw.addWidget(self.statusbar)
        cl.addWidget(status_wrap)

        outer.addStretch(1)
        outer.addWidget(content)
        outer.addStretch(1)
        self.setCentralWidget(central)
        self.var_status.connect(lambda s: self.status_lbl.setText(s))
        self.var_status.set(self.tr("status_ready"))
        self._refresh_rec_info()
        self.coords_lbl.setText(f"●  mouse (0, 0) · {self._res_text}")

    def _build_clicker_tab(self, lay):
        f1, v1 = card(self.tr("target"))
        r = row(v1)
        r.addWidget(Segmented([("follow", self.tr("pos_mode_follow")),
                               ("fixed", self.tr("pos_mode_fixed")),
                               ("multi", self.tr("pos_mode_multi"))],
                              self.V["pos_mode"], height=28))
        r.addStretch(1)
        self._pick_btn = Pill(Var(self.tr("pick_current")), on_click=self._use_current_pos,
                              kind="secondary")
        r.addWidget(self._pick_btn)
        self.xy_row = QWidget()
        self.xy_row.setStyleSheet("background: transparent;")
        r2 = QHBoxLayout(self.xy_row)
        r2.setContentsMargins(0, 1, 0, 1)
        r2.setSpacing(8)
        r2.addWidget(QLabel(self.tr("x")))
        r2.addWidget(self._entry(self.V["pos_x"], 90))
        r2.addSpacing(6)
        r2.addWidget(QLabel(self.tr("y")))
        r2.addWidget(self._entry(self.V["pos_y"], 90))
        r2.addStretch(1)
        v1.addWidget(self.xy_row)

        # 多点循环坐标列表（仅 multi 模式显示）
        self.points_box = QWidget()
        self.points_box.setStyleSheet("background: transparent;")
        pv = QVBoxLayout(self.points_box)
        pv.setContentsMargins(0, 2, 0, 0)
        pv.setSpacing(4)
        self.points_list = PointsList(initial=self.V["points"].get(),
                                      hint_fn=lambda: self.tr("points_empty"))
        self.points_list.changed.connect(lambda pts: self.V["points"].set(pts))
        self.V["points"].connect(self.points_list.set_points)
        pv.addWidget(self.points_list)
        v1.addWidget(self.points_box)
        self.points_box.setVisible(self.V["pos_mode"].get() == "multi")
        self.xy_row.setVisible(self.V["pos_mode"].get() != "multi")
        self.V["pos_mode"].connect(lambda m: self._on_mode_changed(m))
        lay.addWidget(f1)

        f2, v2 = card(self.tr("timing"))
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel(self.tr("interval")), 0, 0)
        e = self._entry(self.V["interval"], 80)
        e.setToolTip(self.tr("tip_interval"))
        g.addWidget(e, 0, 1)
        g.addWidget(Segmented([("ms", "ms"), ("s", "s")], self.V["unit"],
                              height=26, pad=20, min_w=42), 0, 2)
        g.addWidget(QLabel(self.tr("jitter")), 1, 0)
        e = self._entry(self.V["jitter"], 80)
        e.setToolTip(self.tr("tip_jitter"))
        g.addWidget(e, 1, 1)
        g.addWidget(Segmented([("ms", "ms"), ("s", "s")],
                              self.V["jitter_unit"], height=26, pad=20, min_w=42), 1, 2)
        g.setColumnStretch(3, 1)
        v2.addLayout(g)
        r3 = row(v2)
        r3.addWidget(Switch(self.V["human"]))
        hcol = QVBoxLayout()
        hcol.setSpacing(0)
        ht = QLabel(self.tr("human"))
        ht.setStyleSheet("font-weight:600;")
        hs = QLabel(self.tr("human_sub"))
        hs.setObjectName("muted")
        hcol.addWidget(ht)
        hcol.addWidget(hs)
        r3.addLayout(hcol)
        r3.addStretch(1)
        pv = QLabel("")
        pv.setObjectName("muted")
        pv.setWordWrap(True)
        pv.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.var_preview.connect(pv.setText)
        pv.setText(self.var_preview.get())
        v2.addWidget(pv)
        lay.addWidget(f2)

        f3, v3 = card(self.tr("behavior"))
        ra = row(v3)
        ra.addWidget(QLabel(self.tr("click_action")))
        ra.addStretch(1)
        ra.addWidget(Segmented([("single", self.tr("action_single")),
                                ("double", self.tr("action_double")),
                                ("drag", self.tr("action_drag"))],
                               self.V["click_action"], height=26))
        sep(v3)
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel(self.tr("mouse_button")), 0, 0)
        g.addWidget(Segmented([("left", self.tr("left")), ("right", self.tr("right"))],
                              self.V["button"], height=26, pad=20, min_w=40), 0, 1)
        g.addWidget(QLabel(self.tr("pos_jitter")), 1, 0)
        e = self._entry(self.V["pos_jitter"], 80)
        e.setToolTip(self.tr("tip_posj"))
        g.addWidget(e, 1, 1)
        g.addWidget(caption(self.tr("pos_jitter_unit")), 1, 2)
        g.addWidget(QLabel(self.tr("loops")), 2, 0)
        g.addWidget(self._entry(self.V["loops"], 80), 2, 1)
        g.addWidget(caption(self.tr("loops_unit")), 2, 2)
        g.setColumnStretch(3, 1)
        v3.addLayout(g)
        lay.addWidget(f3)

        self.btn_click = QPushButton(self.var_btn_click.get())
        self.btn_click.setObjectName("hero")
        self.var_btn_click.connect(self.btn_click.setText)
        self.btn_click.clicked.connect(self.toggle_clicker)
        self.btn_click.setCursor(Qt.CursorShape.PointingHandCursor)
        lay.addWidget(self.btn_click)
        lay.addStretch(1)

    def _build_record_tab(self, lay):
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 2)
        self.btn_rec = Pill(self.var_btn_rec, on_click=self.toggle_record, kind="primary")
        self.btn_play = Pill(self.var_btn_play, on_click=self.toggle_play, kind="primary")
        bar.addWidget(self.btn_rec)
        bar.addWidget(self.btn_play)
        bar.addWidget(Pill(Var(self.tr("clear")), on_click=self._clear_rec, kind="secondary"))
        bar.addStretch(1)
        bar.addWidget(Pill(Var(self.tr("load_script")), on_click=self._load_script, kind="secondary"))
        bar.addWidget(Pill(Var(self.tr("save_script")), on_click=self._save_script, kind="secondary"))
        lay.addLayout(bar)

        f1, v1 = card(self.tr("rec_card"))
        self.rec_info_lbl = QLabel("")
        self.rec_info_lbl.setStyleSheet("font-weight:600;")
        self.var_rec_info.connect(self.rec_info_lbl.setText)
        self.rec_info_lbl.setText(self.var_rec_info.get())
        v1.addWidget(self.rec_info_lbl)
        lay.addWidget(f1)

        f2, v2 = card(self.tr("play_card"))
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(6)
        rows = (("speed", "speed", "tip_speed", None),
                ("rec_jitter", "rec_jitter", None, "rec_jitter_unit"),
                ("rec_pos_jitter", "rec_pos_jitter", None, "rec_pos_jitter_unit"),
                ("rec_loops", "rec_loops", None, "rec_loops_unit"))
        for i, (key, var, tip, unit) in enumerate(rows):
            g.addWidget(QLabel(self.tr(key)), i, 0)
            e = self._entry(self.V[var], 80)
            if tip:
                e.setToolTip(self.tr(tip))
            g.addWidget(e, i, 1)
            if unit:
                g.addWidget(caption(self.tr(unit)), i, 2)
        g.addWidget(Switch(self.V["rec_human"]), 4, 0)
        g.addWidget(QLabel(self.tr("rec_human")), 4, 1)
        g.setColumnStretch(3, 1)
        v2.addLayout(g)
        lay.addWidget(f2)

        f4, v4 = card(self.tr("script_lib"))
        r = row(v4)
        self.lib_combo = QComboBox()
        self.lib_combo.setMinimumHeight(30)
        self.lib_combo.currentTextChanged.connect(self._lib_autoload)
        r.addWidget(self.lib_combo, 1)
        r.addWidget(Pill(Var(self.tr("lib_save")), on_click=self._lib_save, kind="secondary"))
        r.addWidget(Pill(Var(self.tr("lib_del")), on_click=self._lib_del, kind="secondary"))
        self._lib_refresh()
        lay.addWidget(f4)
        lay.addStretch(1)

    def _build_settings_tab(self, lay):
        f1, v1 = card(self.tr("general"))
        r = row(v1)
        r.addWidget(QLabel(self.tr("language")))
        r.addStretch(1)
        r.addWidget(Segmented([("zh", "中文"), ("en", "English")],
                              Var(self.lang),
                              on_change=lambda v: self._switch_lang(v), height=28))
        sep(v1)
        r2 = row(v1)
        r2.addWidget(QLabel(self.tr("appearance")))
        r2.addStretch(1)
        r2.addWidget(Segmented([("light", self.tr("theme_light")),
                                ("dark", self.tr("theme_dark"))],
                               Var(self.theme),
                               on_change=lambda v: self._switch_theme(v), height=28))
        sep(v1)
        r3 = row(v1)
        r3.addWidget(QLabel(self.tr("auto_load")))
        r3.addStretch(1)
        r3.addWidget(Switch(self.V["auto_load"]))
        sep(v1)
        r4 = row(v1)
        c4 = QVBoxLayout()
        c4.setSpacing(0)
        ct = QLabel(self.tr("corner_stop"))
        ct.setStyleSheet("font-weight:600;")
        cs = QLabel(self.tr("corner_sub"))
        cs.setObjectName("muted")
        c4.addWidget(ct)
        c4.addWidget(cs)
        r4.addLayout(c4)
        r4.addStretch(1)
        r4.addWidget(Switch(self.V["corner_stop"]))
        sep(v1)
        r5 = row(v1)
        r5.addWidget(QLabel(self.tr("close_to_tray")))
        r5.addStretch(1)
        r5.addWidget(Switch(self.V["close_to_tray"]))
        lay.addWidget(f1)

        f2, v2 = card(self.tr("cfg_card"))
        r = row(v2)
        r.addStretch(1)
        r.addWidget(Pill(Var(self.tr("import_cfg")), on_click=self._import_cfg, kind="primary"))
        r.addWidget(Pill(Var(self.tr("export_cfg")), on_click=self._export_cfg, kind="primary"))
        v2.addWidget(caption(self.tr("cfg_note")))
        lay.addWidget(f2)

        f3, v3 = card(self.tr("about"))
        v3.addWidget(caption(f"{APP_NAME} · v4.6 · Windows 10/11"))
        v3.addWidget(caption("F6 连点 · F8 录制 · F9 回放" if self.lang == "zh"
                             else "F6 Click · F8 Record · F9 Replay"))
        lay.addWidget(f3)
        lay.addStretch(1)

    def _build_help_tab(self, lay):
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(HELP_TEXT[self.lang])
        lay.addWidget(txt, 1)

    def _entry(self, var, width):
        e = QLineEdit(var.get())
        e.setFixedWidth(width)
        e.setFixedHeight(28)
        var.connect(e.setText)
        e.textChanged.connect(lambda s: var.set(s))
        return e

    def _switch_lang(self, lang):
        if lang == self.lang:
            return
        self.lang = lang
        self._rebuild_central()

    def _switch_theme(self, t):
        if t == self.theme or t not in THEMES:
            return
        self.theme = t
        self.V["theme"].set(t)
        CUR.clear()
        CUR.update(THEMES[t])
        QApplication.instance().setStyleSheet(make_qss(CUR))
        self._rebuild_central()
        QTimer.singleShot(120, lambda: apply_window_chrome(int(self.winId()), CUR["BG"]))

    def _toggle_theme(self):
        self._switch_theme("dark" if self.theme == "light" else "light")

    def _on_mode_changed(self, m):
        multi = m == "multi"
        if hasattr(self, "points_box"):
            self.points_box.setVisible(multi)
        if hasattr(self, "xy_row"):
            self.xy_row.setVisible(m != "multi")
        self._fit_window()

    def _rebuild_central(self):
        old = self.takeCentralWidget()
        old.deleteLater()
        self.var_status = Var(self.tr("status_ready"))
        self._build_central()
        self._update_preview()      # 预览/录制信息随语言重建
        self._refresh_rec_info()
        self._fit_window()

    def _fit_window(self):
        """窗口大小按各页实际内容自适应（中文窄、英文宽），高度贴合内容。"""
        pages = [self.tabs.widget(i) for i in range(self.tabs.count())]
        w = max(p.sizeHint().width() for p in pages) + 40
        h = max(560, self.centralWidget().sizeHint().height())
        self.setFixedSize(min(700, max(520, w)), h)

    # ---------- 事件泵 ----------
    def _pump(self):
        try:
            while True:
                fn = self._ui_q.get_nowait()
                fn()
        except queue.Empty:
            pass
        x, y = self._last_pos
        if hasattr(self, "coords_lbl"):
            full = f"●  mouse ({x}, {y}) · {self._res_text}"
            fm = self.coords_lbl.fontMetrics()
            self.coords_lbl.setText(fm.elidedText(full, Qt.TextElideMode.ElideRight,
                                                  max(80, self.coords_lbl.width() - 4)))
        if self._rec_dirty:
            self._rec_dirty = False
            self._refresh_rec_info()
        if self.clicking:
            state, color = self.tr("state_click"), GREEN
        elif self.recording:
            state, color = self.tr("state_rec"), RED
        elif self.playing:
            state, color = self.tr("state_play"), ORANGE
        else:
            state, color = self.tr("state_idle"), CUR["MUTED"]
        self.state_lbl.setText("● " + state)
        self.state_lbl.setStyleSheet(
            f"background:{color};color:white;border-radius:9px;"
            "font-weight:600;font-size:12px;padding:3px 11px;")
        self.var_btn_click.set(self.tr("stop_click") if self.clicking else self.tr("start"))
        self.var_btn_rec.set(self.tr("stop_rec") if self.recording else self.tr("record"))
        self.var_btn_play.set(self.tr("stop_play") if self.playing else self.tr("play"))
        try:
            self.btn_click.setStyleSheet(
                f"background:{RED};color:white;border:none;border-radius:20px;"
                "min-height:40px;font-size:14px;font-weight:600;"
                if self.clicking else "")
        except RuntimeError:
            pass
        try:
            self.btn_rec.set_kind("danger" if self.recording else "primary")
            self.btn_play.set_kind("danger" if self.playing else "primary")
            self.tray_act_show.setText(self.tr("tray_show"))
            self.tray_act_click.setText(self.tr("menu_stop_click") if self.clicking else self.tr("menu_click"))
            self.tray_act_rec.setText(self.tr("menu_stop_rec") if self.recording else self.tr("menu_rec"))
            self.tray_act_play.setText(self.tr("menu_stop_play") if self.playing else self.tr("menu_play"))
        except (RuntimeError, AttributeError):
            pass

    def _set_status(self, s):
        self._ui_q.put(lambda s=s: self.var_status.set(s))

    # ---------- 参数 ----------
    def _get_float(self, var, default=0.0):
        try:
            return float(var.get())
        except (ValueError, TypeError):
            return default

    def _get_int(self, var, default=0):
        try:
            return int(float(var.get()))
        except (ValueError, TypeError):
            return default

    def _interval_ms(self):
        interval = self._get_float(self.V["interval"], 200) * (
            1000.0 if self.V["unit"].get() == "s" else 1.0)
        jitter = max(0.0, self._get_float(self.V["jitter"], 0)) * (
            1000.0 if self.V["jitter_unit"].get() == "s" else 1.0)
        return interval, jitter

    @staticmethod
    def _fmt_ms(ms):
        return f"{ms / 1000:g}s" if ms >= 1000 else f"{ms:g}ms"

    def _update_preview(self):
        interval, jitter = self._interval_ms()
        lo = max(0.005, interval - jitter)
        hi = interval + jitter
        mode = self.tr("mode_gauss") if self.V["human"].get() else self.tr("mode_uniform")
        self.var_preview.set(self.tr("preview_fmt").format(
            i=self._fmt_ms(interval), lo=self._fmt_ms(lo), hi=self._fmt_ms(hi), mode=mode))

    def _use_current_pos(self):
        """3 秒倒计时后捕获当前鼠标位置。"""
        if getattr(self, "_picking", False):
            return
        self._picking = True
        self._pick_left = 3
        btn = self.sender() if hasattr(self, "sender") else None
        self._pick_btn = btn or getattr(self, "_pick_btn", None)

        def tick():
            if not self._picking:
                return
            if self._pick_left <= 0:
                self._picking = False
                x, y = self._last_pos
                if self.V["pos_mode"].get() == "multi":
                    self.points_list.add_point(x, y)   # 多点模式：追加进列表
                else:
                    self.V["pos_mode"].set("fixed")
                    self.V["pos_x"].set(str(x))
                    self.V["pos_y"].set(str(y))
                if self._pick_btn:
                    self._pick_btn.setEnabled(True)
                    self._pick_btn.setText(self.tr("pick_current"))
                self._set_status(self.tr("pick_ok").format(x=x, y=y))
                return
            self._set_status(self.tr("picking").format(n=self._pick_left))
            if self._pick_btn:
                self._pick_btn.setText(self.tr("pick_countdown").format(n=self._pick_left))
            self._pick_left -= 1
            QTimer.singleShot(1000, tick)

        if self._pick_btn:
            self._pick_btn.setEnabled(False)
        tick()

    def _start_coord_polling(self):
        def poll():
            while True:
                self._poll_once()
                time.sleep(0.1)
        threading.Thread(target=poll, daemon=True).start()

    def _poll_once(self):
        """单次轮询：更新坐标 + 紧急停止检测（可被测试直接调用）。"""
        try:
            pos = cursor_pos()
            self._last_pos = pos
            running = self.clicking or self.playing or self.recording
            in_corner = pos[0] <= 10 and pos[1] <= 10
            if running and in_corner and self._corner_armed \
                    and self.V["corner_stop"].get():
                self._corner_armed = False

                def emergency():
                    if self.clicking:
                        self.toggle_clicker()
                    if self.playing:
                        self.toggle_play()
                    if self.recording:
                        self.toggle_record()
                    self._set_status(self.tr("corner_stopped"))
                    try:
                        self.tray.showMessage(APP_NAME, self.tr("corner_stopped"),
                                              QIcon(resource_path("icon.ico")), 2000)
                    except Exception:
                        pass
                self._ui_q.put(emergency)
            elif not in_corner:
                self._corner_armed = True
        except Exception:
            pass

    # ---------- 连点 ----------
    def toggle_clicker(self):
        if self.clicking:
            self.clicker_stop.set()
            return
        if (self.V["pos_mode"].get() == "multi"
                and not self.V["points"].get()):
            self._msg(self.tr("points_empty"))
            return
        self.tabs.setCurrentIndex(0)     # 热键触发时跳到对应页，状态可见
        if self._last_pos[0] <= 10 and self._last_pos[1] <= 10:
            self._corner_armed = False
        self.clicking = True        # 同步置位：快速重复触发不会重复启动线程
        self.clicker_stop = threading.Event()
        threading.Thread(target=self._clicker_loop, args=(self.clicker_stop,),
                         daemon=True).start()

    def _clicker_loop(self, stop):
        interval, jitter = self._interval_ms()
        interval = max(10.0, interval)
        V = self.V
        pos_j = max(0, self._get_int(V["pos_jitter"], 0))
        loops = max(0, self._get_int(V["loops"], 0))
        btn = V["button"].get()
        mode = V["pos_mode"].get()
        fx = self._get_int(V["pos_x"], 0)
        fy = self._get_int(V["pos_y"], 0)
        pts = [(int(p[0]), int(p[1])) for p in (V["points"].get() or [])]
        human = V["human"].get()
        if mode == "multi" and not pts:
            self.clicking = False
            return
        # 多点循环：循环次数按“完整轮数”计；单点模式按点击次数计
        total = loops * len(pts) if mode == "multi" and loops > 0 else loops

        n = 0
        pi = 0
        while not stop.is_set() and (total == 0 or n < total):
            if mode == "fixed":
                x, y = fx, fy
                nx, ny = x + random.randint(-3, 3), y + random.randint(-3, 3)
            elif mode == "multi":
                x, y = pts[pi % len(pts)]
                nx, ny = pts[(pi + 1) % len(pts)]   # 拖动模式的目的地
                pi += 1
            else:
                x, y = cursor_pos()
                nx, ny = x + random.randint(-3, 3), y + random.randint(-3, 3)
            dx, dy = human_offset(pos_j, human)
            x, y = x + dx, y + dy
            act = V["click_action"].get()
            if act == "double":
                do_click(x, y, btn)
                gap = time.time() + random.uniform(0.08, 0.13)
                while time.time() < gap and not stop.is_set():
                    time.sleep(0.005)
                if stop.is_set():
                    break
                do_click(x, y, btn)          # 同点位第二击，保证系统判定为双击
            elif act == "drag":
                send_move(x, y)
                time.sleep(0.02)
                send_button(btn, True)
                time.sleep(random.uniform(0.25, 0.45))
                replay_move(nx, ny, stop, step=24, pause=0.006)   # 平滑拖到目标
                time.sleep(random.uniform(0.05, 0.12))
                send_button(btn, False)
            else:
                do_click(x, y, btn)
            n += 1
            self._set_status(self.tr("clicking").format(n=n))
            deadline = time.time() + human_interval_ms(interval, jitter, human)
            while not stop.is_set() and time.time() < deadline:
                time.sleep(0.005)   # sleep 轮询：绝不卡死（Event.wait 在此环境偶发不唤醒）
        self.clicking = False
        self._set_status(self.tr("click_done").format(n=n))

    # ---------- 录制 ----------
    def toggle_record(self):
        if self.playing:
            self._msg(self.tr("need_stop_play"))
            return
        if self.recording:
            self.recording = False
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
            c, m = self._rec_counts()
            self._set_status(self.tr("rec_done").format(c=c, m=m))
        else:
            if self.mouse_listener:
                return
            self.recorded = []
            self._coord_mismatch = 0
            self._last_rec_move = (0, 0, 0.0)
            self.rec_start = time.perf_counter()
            self.recording = True
            self.mouse_listener = mouse.Listener(
                on_click=self._on_rec_click, on_move=self._on_rec_move)
            self.mouse_listener.start()
            self._set_status(self.tr("recording"))
            self.tabs.setCurrentIndex(1)     # 热键触发时跳到录制页
        self._refresh_rec_info()

    def _rec_counts(self):
        c = sum(1 for e in self.recorded if e.get("type") in ("down", "click"))
        m = sum(1 for e in self.recorded if e.get("type") == "move")
        return c, m

    def _refresh_rec_info(self):
        c, m = self._rec_counts()
        check = self.tr("rec_ok") if self._coord_mismatch <= 3 \
            else self.tr("rec_bad").format(n=self._coord_mismatch)
        if c == 0 and m == 0 and not self.recording:
            self.var_rec_info.set(self.tr("rec_none"))
        else:
            self.var_rec_info.set(self.tr("rec_info_fmt").format(c=c, m=m, check=check))

    def _on_rec_move(self, x, y):
        # 钩子回调必须极快且绝不抛异常；界面更新只置脏标记
        try:
            if not self.recording:
                return
            now = time.perf_counter()
            if now - self._last_rec_move[2] < 0.04:
                return
            self._last_rec_move = (x, y, now)
            self.recorded.append({"t": round(now - self.rec_start, 4),
                                  "type": "move", "x": x, "y": y})
            self._rec_dirty = True
        except Exception:
            pass

    def _on_rec_click(self, x, y, button, pressed):
        try:
            if not self.recording or button.name not in ("left", "right"):
                return
            now = time.perf_counter()
            try:
                gx, gy = cursor_pos()
                d = max(abs(gx - x), abs(gy - y))
                if d > 3 and d > self._coord_mismatch:
                    self._coord_mismatch = d
            except Exception:
                pass
            self.recorded.append({"t": round(now - self.rec_start, 4),
                                  "type": "down" if pressed else "up",
                                  "x": x, "y": y, "button": button.name})
            self._rec_dirty = True
        except Exception:
            pass

    def _clear_rec(self):
        if self.recording or self.playing:
            return
        self.recorded = []
        self._coord_mismatch = 0
        self._refresh_rec_info()
        self._set_status(self.tr("cleared"))

    # ---------- 回放 ----------
    def toggle_play(self):
        if self.recording:
            self._msg(self.tr("need_stop_rec"))
            return
        if self.playing:
            self.play_stop.set()
            return
        if not self.recorded:
            self._msg(self.tr("need_record"))
            return
        self.playing = True              # 同步置位
        self.tabs.setCurrentIndex(1)     # 热键触发时跳到录制页
        if self._last_pos[0] <= 10 and self._last_pos[1] <= 10:
            self._corner_armed = False
        self.play_stop = threading.Event()
        threading.Thread(target=self._play_loop, args=(self.play_stop,),
                         daemon=True).start()

    def _play_loop(self, stop):
        V = self.V
        speed = max(0.1, self._get_float(V["speed"], 1.0))
        jit = max(0, self._get_float(V["rec_jitter"], 0))
        pos_j = max(0, self._get_int(V["rec_pos_jitter"], 0))
        loops = max(0, self._get_int(V["rec_loops"], 1))
        human = V["rec_human"].get()
        events = self.recorded
        if not events:
            self.playing = False
            return
        pairs, spans = detect_double_clicks(events)

        total = 0
        for lap in range(loops if loops > 0 else 10 ** 9):
            if stop.is_set():
                break
            gaps = []
            prev = 0.0
            for i, ev in enumerate(events):
                g = (ev["t"] - prev) / speed
                if i in spans:   # 双击对内部：不走神、钳制在系统双击窗口内
                    g += (random.uniform(-jit, jit) if jit else 0.0) / 1000.0
                    g = min(max(g, 0.02), 0.28)
                else:
                    g = max(0.005, g + _jitter_bonus_ms(jit, human) / 1000.0)
                gaps.append(g)
                prev = ev["t"]

            t0 = time.perf_counter()
            target = 0.0
            first_offs = {}
            gesture_off = (0, 0)
            for i, (ev, gap) in enumerate(zip(events, gaps)):
                if stop.is_set():
                    break
                target += gap
                wait = t0 + target - time.perf_counter()
                if wait > 0:
                    end_t = time.time() + wait
                    while time.time() < end_t and not stop.is_set():
                        time.sleep(0.005)
                    if stop.is_set():
                        break
                typ = ev.get("type", "click")
                if typ == "move":
                    dx, dy = human_offset(pos_j, human)
                    replay_move(ev["x"] + dx, ev["y"] + dy, stop)
                elif typ == "down":
                    if i in pairs and pairs[i] in first_offs:
                        off = first_offs[pairs[i]]
                    else:
                        off = human_offset(pos_j, human)
                        first_offs[i] = off
                    gesture_off = off
                    send_move(ev["x"] + off[0], ev["y"] + off[1])
                    time.sleep(0.01)
                    send_button(ev["button"], True)
                elif typ == "up":
                    off = gesture_off
                    send_move(ev["x"] + off[0], ev["y"] + off[1])
                    time.sleep(random.uniform(0.015, 0.045))
                    send_button(ev["button"], False)
                else:
                    if i in pairs and pairs[i] in first_offs:
                        off = first_offs[pairs[i]]
                    else:
                        off = human_offset(pos_j, human)
                        first_offs[i] = off
                    gesture_off = off
                    do_click(ev["x"] + off[0], ev["y"] + off[1], ev["button"])
                total += 1
                self._set_status(self.tr("playing").format(l=lap + 1, n=total))
        self.playing = False
        self._set_status(self.tr("play_done").format(n=total))

    # ---------- 脚本 ----------
    def _save_script(self):
        if self.recording:
            self._msg(self.tr("need_stop_save"))
            return
        if not self.recorded:
            self._msg(self.tr("nothing_saved"))
            return
        path, _ = QFileDialog.getSaveFileName(self, "JSON", "script.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(self.recorded, fp, ensure_ascii=False, indent=1)
        self._set_status(self.tr("saved_to").format(p=path))

    def _load_script(self):
        if self.recording or self.playing:
            self._msg(self.tr("nothing_loaded"))
            return
        path, _ = QFileDialog.getOpenFileName(self, "JSON", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            self.recorded = self._normalize_events(data)
            self._coord_mismatch = 0
            self._refresh_rec_info()
            self._set_status(self.tr("loaded_from").format(p=path))
        except Exception as e:
            self._msg(self.tr("load_fail") + chr(10) + str(e), error=True)

    @staticmethod
    def _normalize_events(data):
        out = []
        for e in data:
            if not isinstance(e, dict) or not {"t", "x", "y"} <= set(e):
                continue
            if "type" not in e:
                if "button" not in e:
                    continue
                e["type"] = "click"
            out.append(e)
        return out

    # ---------- 脚本库 ----------
    def _lib_refresh(self):
        self.lib_combo.blockSignals(True)
        cur = self.lib_combo.currentText()
        self.lib_combo.clear()
        for name in sorted(self.library):
            self.lib_combo.addItem(name)
        if cur in self.library:
            self.lib_combo.setCurrentText(cur)
        self.lib_combo.blockSignals(False)

    def _lib_save(self):
        if self.recording:
            self._msg(self.tr("need_stop_save"))
            return
        if not self.recorded:
            self._msg(self.tr("lib_nothing"))
            return
        default = f"{self.tr('lib_default')} {len(self.library) + 1}"
        name, ok = QInputDialog.getText(self, self.tr("script_lib"),
                                        self.tr("lib_name"), text=default)
        if not ok or not name.strip():
            return
        name = name.strip()
        self.library[name] = json.loads(json.dumps(self.recorded))
        self._lib_save_file()
        self._lib_refresh()
        self.lib_combo.setCurrentText(name)
        self._set_status(self.tr("lib_saved").format(s=name))

    def _lib_autoload(self, name):
        # 下拉框选中即切换脚本（录制/回放进行中忽略）
        if self.recording or self.playing or name not in self.library:
            return
        self.recorded = self._normalize_events(self.library[name])
        self._coord_mismatch = 0
        self._refresh_rec_info()
        self._set_status(self.tr("lib_loaded").format(s=name))

    def _lib_del(self):
        name = self.lib_combo.currentText()
        if name not in self.library:
            return
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Icon.NoIcon)
        box.setText(self.tr("lib_confirm").format(s=name))
        box.setStandardButtons(QMessageBox.StandardButton.Yes
                               | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        try:
            lbl = box.findChild(QLabel)
            if lbl:
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
        if not os.environ.get("AC_TEST"):
            if box.exec() != QMessageBox.StandardButton.Yes:
                return      # 交互模式：用户拒绝则取消删除
        # 测试环境：默认确认，继续删除
        del self.library[name]
        self._lib_save_file()
        self._lib_refresh()
        self._set_status(self.tr("lib_deleted").format(s=name))

    # ---------- 配置导入/导出 ----------
    def _export_cfg(self):
        if self.recording:
            self._msg(self.tr("need_stop_save"))
            return
        path, _ = QFileDialog.getSaveFileName(self, "JSON",
                                              "autoclicker_profile.json", "JSON (*.json)")
        if not path:
            return
        data = {"app": APP_NAME, "version": CFG_VERSION, "language": self.lang,
                "settings": self._settings_snapshot(), "script": self.recorded}
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=1)
        self._set_status(self.tr("cfg_saved").format(p=path))

    def _import_cfg(self):
        if self.recording or self.playing:
            self._msg(self.tr("nothing_loaded"))
            return
        path, _ = QFileDialog.getOpenFileName(self, "JSON", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if data.get("app") != APP_NAME:
                raise ValueError(self.tr("invalid_cfg"))
            self._apply_settings(data.get("settings", {}))
            self.recorded = self._normalize_events(data.get("script", []))
            self._coord_mismatch = 0
            if data.get("language") in ("zh", "en") and data["language"] != self.lang:
                self._switch_lang(data["language"])
            self._refresh_rec_info()
            self._set_status(self.tr("cfg_loaded").format(p=path))
        except Exception as e:
            self._msg(self.tr("cfg_fail") + chr(10) + str(e), error=True)

    # ---------- 热键 ----------
    def _start_hotkeys(self):
        h = keyboard.GlobalHotKeys({
            "<f6>": lambda: self._ui_q.put(self.toggle_clicker),
            "<f8>": lambda: self._ui_q.put(self.toggle_record),
            "<f9>": lambda: self._ui_q.put(self.toggle_play),
        })
        h.daemon = True
        h.start()
        self.kb_listener = h

    # ---------- 托盘 ----------
    def _create_tray(self):
        self.tray = QSystemTrayIcon(QIcon(resource_path("icon.ico")), self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        self.tray_act_show = QAction(self.tr("tray_show"), menu)
        self.tray_act_show.triggered.connect(self._toggle_visible)
        self.tray_act_click = QAction("", menu)
        self.tray_act_click.triggered.connect(lambda: self._ui_q.put(self.toggle_clicker))
        self.tray_act_rec = QAction("", menu)
        self.tray_act_rec.triggered.connect(lambda: self._ui_q.put(self.toggle_record))
        self.tray_act_play = QAction("", menu)
        self.tray_act_play.triggered.connect(lambda: self._ui_q.put(self.toggle_play))
        quit_act = QAction(self.tr("tray_quit"), menu)
        quit_act.triggered.connect(self._quit_app)
        for a in (self.tray_act_show, self.tray_act_click,
                  self.tray_act_rec, self.tray_act_play):
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _on_tray_activated(self, reason):
        # 左键单击/双击托盘图标：显示并聚焦主窗口
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            if not self.isVisible():
                self.showNormal()
            self.raise_()
            self.activateWindow()

    def _quit_app(self):
        self._quit = True
        self.close()

    def closeEvent(self, e):
        if self.V["close_to_tray"].get() and not self._quit:
            e.ignore()
            self.hide()
            if not getattr(self, "_tray_noted", False):
                self._tray_noted = True
                try:
                    self.tray.showMessage(APP_NAME, self.tr("tray_note"),
                                          QIcon(resource_path("icon.ico")), 2000)
                except Exception:
                    pass
            return
        self.clicker_stop.set()
        self.play_stop.set()
        self.recording = False
        self._save_persisted()
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
            if self.kb_listener:
                self.kb_listener.stop()
        except Exception:
            pass
        e.accept()


def enable_dpi_awareness():
    """进程级 Per-Monitor DPI 感知（在 QApplication 创建前调用）。
    保证 GetCursorPos/SendInput/低级钩子三者坐标统一（RDP/缩放环境关键）。"""
    try:
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


def main():
    enable_dpi_awareness()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(make_qss(CUR))
    win = App()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
