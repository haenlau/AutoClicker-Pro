# -*- coding: utf-8 -*-
"""
AutoClicker Pro — Windows 鼠标连点器 & 录制回放
设计语言：Apple 液态玻璃 / macOS 风格（中性灰阶材质、发丝线、大圆角、
药丸控件、按压即反馈、语义色，无 AI 蓝紫）

- 中英双语（跟随系统语言，可切换，设置自动保存）
- 连点：当前鼠标位置或固定坐标，间隔=中心±抖动，拟人化随机
- 录制：完整宏（移动轨迹+按下/抬起，支持拖动、双击），不丢快速点击
- 回放：平滑路径重放，绝对时间轴不漂移，双击对保持有效，拟人化防检测
- 配置导入/导出

热键（全局）: F6=连点  F8=录制  F9=回放
"""
import ctypes
import json
import os
import queue
import random
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText

from pynput import mouse, keyboard

APP_NAME = "AutoClicker Pro"
CFG_VERSION = 3

# ---------------- i18n ----------------
TR = {
    "zh": {
        "app_title": "鼠标连点器 & 录制回放",
        "tab_clicker": "自动连点", "tab_record": "录制回放",
        "tab_settings": "设置", "tab_help": "帮助",
        "target": "目标位置", "timing": "点击节奏", "behavior": "点击方式",
        "pos_mode_follow": "跟随鼠标", "pos_mode_fixed": "固定坐标",
        "x": "X", "y": "Y", "pick_current": "填入当前位置",
        "interval": "点击间隔", "jitter": "随机抖动", "same_unit": "同单位",
        "human": "拟人模式", "human_sub": "高斯分布随机 + 偶尔走神停顿，防统计检测",
        "pos_jitter": "位置偏移 (px)", "mouse_button": "鼠标按键",
        "left": "左键", "right": "右键", "loops": "循环次数", "loops_unit": "次 (0=无限)",
        "start": "开始连点 · F6", "stop_click": "停止连点 · F6",
        "record": "● 录制", "stop_rec": "■ 停止录制", "play": "▶ 回放", "stop_play": "■ 停止回放",
        "clear": "清空", "save_script": "导出脚本", "load_script": "导入脚本",
        "export_cfg": "导出配置", "import_cfg": "导入配置",
        "rec_card": "录制状态", "play_card": "回放设置",
        "speed": "速度倍率", "rec_jitter": "间隔抖动 (ms)", "rec_pos_jitter": "位置偏移 (px)",
        "rec_loops": "循环次数", "rec_human": "拟人模式",
        "rec_none": "尚未录制 — 按 F8 开始，移动轨迹与按下抬起都会记录",
        "rec_ok": "坐标自检正常", "rec_bad": "坐标自检偏差约 {n}px",
        "rec_info_fmt": "{c} 次点击 · {m} 个移动点 · {check}",
        "general": "通用", "cfg_card": "配置管理", "cfg_note": "设置自动保存到本机。导出的配置包含全部参数与录制脚本，可在其他电脑导入还原。",
        "auto_load": "启动时恢复上次设置", "about": "关于",
        "language": "界面语言",
        "state_idle": "空闲", "state_click": "连点中", "state_rec": "录制中", "state_play": "回放中",
        "status_ready": "就绪",
        "pick_ok": "已填入当前鼠标坐标 ({x}, {y})",
        "clicking": "连点中… 已点击 {n} 次", "click_done": "连点结束，共 {n} 次",
        "recording": "录制中… (F8 停止)",
        "rec_done": "录制结束：{c} 次点击，{m} 个移动点",
        "playing": "回放中… 第 {l} 轮 {n} 步", "play_done": "回放结束，共执行 {n} 步",
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
        "x": "X", "y": "Y", "pick_current": "Use current",
        "interval": "Interval", "jitter": "Jitter", "same_unit": "same unit",
        "human": "Humanize", "human_sub": "Gaussian randomness + occasional pauses, resists detection",
        "pos_jitter": "Position offset (px)", "mouse_button": "Button",
        "left": "Left", "right": "Right", "loops": "Loops", "loops_unit": "(0 = infinite)",
        "start": "Start Clicking · F6", "stop_click": "Stop Clicking · F6",
        "record": "● Record", "stop_rec": "■ Stop Recording", "play": "▶ Replay", "stop_play": "■ Stop Replay",
        "clear": "Clear", "save_script": "Export Script", "load_script": "Import Script",
        "export_cfg": "Export Config", "import_cfg": "Import Config",
        "rec_card": "Recording", "play_card": "Playback Settings",
        "speed": "Speed", "rec_jitter": "Interval jitter (ms)", "rec_pos_jitter": "Position offset (px)",
        "rec_loops": "Loops", "rec_human": "Humanize",
        "rec_none": "Nothing recorded — press F8; moves and press/release are captured",
        "rec_ok": "coord check OK", "rec_bad": "coord check ~{n}px off",
        "rec_info_fmt": "{c} clicks · {m} move points · {check}",
        "general": "General", "cfg_card": "Configuration", "cfg_note": "Settings persist automatically. Exported config contains all parameters and the recorded script — import it on another PC.",
        "auto_load": "Restore last settings on startup", "about": "About",
        "language": "Language",
        "state_idle": "Idle", "state_click": "Clicking", "state_rec": "Recording", "state_play": "Replaying",
        "status_ready": "Ready",
        "pick_ok": "Filled current mouse position ({x}, {y})",
        "clicking": "Clicking… {n} clicks", "click_done": "Clicking finished, {n} total",
        "recording": "Recording… (F8 to stop)",
        "rec_done": "Recording done: {c} clicks, {m} move points",
        "playing": "Replaying… lap {l}, {n} steps", "play_done": "Replay finished, {n} steps",
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
    "zh": """【快速上手】
1. 连点：把鼠标移到目标位置（顶栏实时坐标会跟着变），按 F6 开始原地连点，再按 F6 停止。
2. 录制：按 F8 后正常操作（移动、单击、双击、拖动都会被记录），再按 F8 结束。
3. 回放：按 F9 重放刚才的过程，可加速/减速、加抖动、循环。
4. 固定坐标：在“目标位置”选“固定坐标”并点“填入当前位置”，之后连点不再依赖鼠标位置。

【全局热键】（任何窗口下都有效）
  F6  开始/停止 连点      F8  开始/停止 录制      F9  开始/停止 回放

【拟人化防检测】
开启拟人模式后：点击间隔按高斯分布随机（中心密集、偶尔偏快偏慢）；每次点击约 5%
概率插入 80–350ms“走神”停顿；落点按高斯分布偏移；鼠标按下时长随机。固定周期是最
容易被统计方式识别的机器特征，建议始终开启。

【常见问题】
· 录不到某些窗口的点击？
  目标程序若以管理员身份运行，普通权限的程序收不到它的输入事件。右键本软件
  →“以管理员身份运行”再录制。
· 通过远程桌面(RDP)连接无屏电脑使用？
  本软件已声明 DPI 感知，坐标系自动统一。注意：录制和回放时保持 RDP 窗口分辨率
  一致；录制期间保持会话连接。
· 回放的双击变成两次单击？
  本软件已自动识别“双击对”：回放时两次点击共用位置偏移、间隔保持在系统双击时限
  内。若仍异常，把“位置偏移”调小（≤3px）。
· 杀毒软件报毒？
  PyInstaller 打包的单文件程序偶发误报，加入白名单即可。
· 点击无效？
  某些游戏/应用使用驱动级输入检测，SendInput 无法生效；模拟器窗口一般正常。请勿
  最小化目标窗口。
""",
    "en": """[Quick Start]
1. Auto click: move the mouse to the target (live coordinates in the header), press F6 to start clicking in place, F6 again to stop.
2. Record: press F8, then work normally (moves, clicks, double-clicks and drags are captured), F8 to finish.
3. Replay: press F9 to replay, with speed control, jitter and loops.
4. Fixed position: choose "Fixed position" in Target and click "Use current"; clicking then no longer follows the mouse.

[Global Hotkeys] (work over any window)
  F6  start/stop clicking     F8  start/stop recording     F9  start/stop replay

[Humanized anti-detection]
With Humanize on: intervals follow a Gaussian distribution (dense near the center,
occasionally faster/slower); each click has ~5% chance of an 80–350 ms micro-pause;
landing points are Gaussian-offset; press duration is randomized. A fixed period is
the easiest machine signature to detect statistically — keep it enabled.

[FAQ]
· Some windows can't be recorded?
  If the target app runs as administrator, a normal-privilege app cannot receive its
  input. Right-click this app → "Run as administrator", then record.
· Using a headless PC via RDP?
  This app is DPI-aware, so coordinate systems unify automatically. Keep the RDP
  window resolution the same between recording and replay; stay connected while recording.
· Replayed double-clicks become two single clicks?
  Double-click pairs are detected automatically: both clicks share one position offset
  and the gap stays within the system double-click time. If it still fails, reduce
  "Position offset" to <= 3 px.
· Antivirus flags the exe?
  Occasional false positive for PyInstaller one-file builds — add an exclusion.
· Clicks have no effect?
  Some games/apps use driver-level input checks that SendInput cannot pass. Emulator
  windows normally work. Do not minimize the target window.
""",
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


def enable_dpi_awareness():
    """物理像素工作。RDP/缩放环境中 GetCursorPos/SendInput 与钩子坐标一致。"""
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


def apply_window_chrome(root, hexcolor="#F2F3F7"):
    """Win11：原生圆角窗口 + 标题栏/边框融入界面底色（液态玻璃的“融框”）。"""
    try:
        dwm = ctypes.WinDLL("dwmapi")
        hwnd = user32.GetParent(root.winfo_id())
        r, g, b = int(hexcolor[1:3], 16), int(hexcolor[3:5], 16), int(hexcolor[5:7], 16)
        colorref = ctypes.c_uint((b << 16) | (g << 8) | r)   # COLORREF = 0x00BBGGRR
        dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 33, ctypes.byref(ctypes.c_uint(2)), 4)      # 圆角
        dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 35, ctypes.byref(colorref), 4)              # 标题栏色
        dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 34, ctypes.byref(colorref), 4)              # 边框色
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


# ---------------- 配置文件路径 ----------------

def config_file():
    for base in ([os.path.dirname(sys.executable)] if getattr(sys, "frozen", False) else []) \
            + [os.path.dirname(os.path.abspath(__file__)),
               os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)]:
        try:
            p = os.path.join(base, "autoclicker_config.json")
            with open(p, "a", encoding="utf-8"):
                pass
            return p
        except OSError:
            continue
    return os.path.join(os.path.expanduser("~"), "autoclicker_config.json")


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


# ---------------- 主题（Apple 液态玻璃风） ----------------

BG = "#F2F3F7"        # 窗口底：冷调浅灰
CARD = "#FDFDFE"      # 玻璃卡面
HAIR = "#E5E7ED"      # 发丝线
SHADOW = "#E4E6EC"    # 卡片软阴影
TEXT = "#1D1D1F"      # 主文字（Apple near-black）
MUTED = "#85858B"     # 次要文字（Apple secondaryLabel）
TRACK = "#ECECEF"     # 分段控制器/开关轨道
FIELD = "#F1F2F4"     # 输入框内嵌面
GRAPHITE = "#3A3A3C"  # 主按钮石墨色
GRAPHITE_H = "#4B4B4E"
GRAPHITE_P = "#2C2C2E"
GREEN = "#34C759"     # iOS green
RED = "#FF453A"       # iOS red
ORANGE = "#FF9500"    # iOS orange

F_TITLE = ("Segoe UI", 14, "bold")
F_BODY = ("Segoe UI", 10)
F_BOLD = ("Segoe UI", 10, "bold")
F_CAP = ("Segoe UI", 9)


def _rr_pts(x0, y0, x1, y1, r):
    """圆角矩形的多边形点：手动采样圆弧，不使用 smooth 样条
    （Tk 8.6 的 smooth polygon 在几何反复变化时可能崩溃）。"""
    import math
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    if r < 0.5:
        return [x0, y0, x1, y0, x1, y1, x0, y1]
    pts = []
    corners = [(x1 - r, y0 + r, -math.pi / 2, 0),
               (x1 - r, y1 - r, 0, math.pi / 2),
               (x0 + r, y1 - r, math.pi / 2, math.pi),
               (x0 + r, y0 + r, math.pi, 3 * math.pi / 2)]
    for cx, cy, a0, a1 in corners:
        for i in range(7):
            a = a0 + (a1 - a0) * i / 6
            pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


def _parent_bg(parent):
    """ttk 容器读不到 bg 属性，回退窗口底色。"""
    try:
        return parent["bg"]
    except (KeyError, tk.TclError):
        return BG


class GlassWidget(tk.Canvas):
    """自定义画布控件基类：变量监听的防御与注销。"""

    def _safe(self, fn):
        try:
            if self.winfo_exists():
                fn()
        except tk.TclError:
            pass

    def _detach(self, e):
        if e.widget is not self:
            return
        try:
            self.var.trace_remove("write", self._tid)
        except Exception:
            pass


class Pill(GlassWidget):
    """药丸按钮：按下立即变色（pointer-down 反馈），松开在按钮内才触发。"""

    KINDS = {
        "primary":   {"n": GRAPHITE, "h": GRAPHITE_H, "p": GRAPHITE_P, "fg": "#FFFFFF"},
        "secondary": {"n": "#FFFFFF", "h": "#F3F4F7", "p": "#E8EAEE", "fg": TEXT},
        "danger":    {"n": RED, "h": "#E63E33", "p": "#CC342B", "fg": "#FFFFFF"},
    }

    def __init__(self, parent, textvariable, command=None, kind="primary",
                 height=36, padx=18, font=None):
        super().__init__(parent, highlightthickness=0, bd=0, bg=_parent_bg(parent))
        self.kind, self.cmd = kind, command
        self.h, self.padx = height, padx
        self.font = font or F_BOLD
        self.var = textvariable
        self._hover = False
        self._press = False
        self._tid = self.var.trace_add("write", lambda *_: self._safe(self._fit))
        self.bind("<Configure>", lambda e: self._safe(self._draw))
        self.bind("<Destroy>", self._detach, add="+")
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._down)
        self.bind("<ButtonRelease-1>", self._up)
        self.configure(cursor="hand2")
        self._fit()

    def _enter(self, _):
        self._hover = True
        self._draw()

    def _leave(self, _):
        self._hover = False
        self._press = False
        self._draw()

    def _down(self, _):
        self._press = True          # 按下即反馈，不等松开
        self._draw()

    def _up(self, e):
        was = self._press
        self._press = False
        self._draw()
        if was and 0 <= e.x < self.winfo_width() and 0 <= e.y < self.winfo_height():
            if self.cmd:
                self.cmd()

    def set_kind(self, kind):
        if kind != self.kind:
            self.kind = kind
            self._draw()

    def _fit(self):
        f = tkfont.Font(font=self.font)
        self.configure(width=int(f.measure(self.var.get())) + self.padx * 2, height=self.h)
        self._draw()

    def _fill(self):
        k = self.KINDS[self.kind]
        return k["p"] if self._press else (k["h"] if self._hover else k["n"])

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        self.create_polygon(_rr_pts(0, 0, w, h, h / 2), fill=self._fill(),
                            outline="", smooth=True)
        self.create_text(w / 2, h / 2, text=self.var.get(),
                         fill=self.KINDS[self.kind]["fg"], font=self.font)


class Segmented(GlassWidget):
    """iOS 分段控制器：灰色轨道 + 白色选中滑块。"""

    def __init__(self, parent, options, variable, on_change=None, height=30):
        super().__init__(parent, highlightthickness=0, bd=0, bg=_parent_bg(parent))
        self.opts = options
        self.var = variable
        self.cb = on_change
        self.h = height
        self._tid = variable.trace_add("write", lambda *_: self._safe(self._fit))
        self.bind("<Configure>", lambda e: self._safe(self._draw))
        self.bind("<Button-1>", self._click)
        self.bind("<Destroy>", self._detach, add="+")
        self.configure(cursor="hand2")
        self._fit()

    def _fit(self):
        f = tkfont.Font(font=F_BODY)
        self.seg_w = max(max(f.measure(lbl) for _, lbl in self.opts) + 30, 58)
        self.configure(width=self.seg_w * len(self.opts), height=self.h)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        n = len(self.opts)
        self.seg_w = w / n
        self.create_polygon(_rr_pts(0, 0, w, h, h / 2), fill=TRACK, outline=HAIR,
                            smooth=True)
        cur = self.var.get()
        fsel = tkfont.Font(font=F_BOLD)
        fnorm = tkfont.Font(font=F_BODY)
        for i, (val, lbl) in enumerate(self.opts):
            x0, cx = i * self.seg_w, (i + 0.5) * self.seg_w
            if val == cur:
                m = 3
                self.create_polygon(_rr_pts(x0 + m, m, x0 + self.seg_w - m, h - m,
                                            (h - 2 * m) / 2),
                                    fill="#FFFFFF", outline=HAIR)
            self.create_text(cx, h / 2, text=lbl,
                             fill=TEXT if val == cur else MUTED,
                             font=fsel if val == cur else fnorm)

    def _click(self, e):
        idx = max(0, min(len(self.opts) - 1, int(e.x / self.seg_w)))
        val = self.opts[idx][0]
        if val != self.var.get():
            self.var.set(val)
            if self.cb:
                self.cb(val)


class Switch(GlassWidget):
    """iOS 拨动开关：绿色轨道 + 白色圆钮，滑动动画。"""

    W, H = 46, 28

    def __init__(self, parent, variable, command=None):
        super().__init__(parent, highlightthickness=0, bd=0, bg=parent["bg"],
                         width=self.W, height=self.H, cursor="hand2")
        self.var = variable
        self.cb = command
        self.pos = 1.0 if variable.get() else 0.0   # 滑钮位置 0..1
        self._anim_job = None
        self._tid = variable.trace_add("write", lambda *_: self._safe(self._animate))
        self.bind("<Button-1>", self._toggle)
        self.bind("<Destroy>", self._detach, add="+")
        self._draw()

    def _toggle(self, _):
        self.var.set(not self.var.get())
        if self.cb:
            self.cb()

    def _animate(self):
        if self._anim_job:
            self.after_cancel(self._anim_job)
        self._step()

    def _step(self):
        target = 1.0 if self.var.get() else 0.0
        d = target - self.pos
        if abs(d) < 0.02:
            self.pos = target
            self._draw()
            self._anim_job = None
            return
        self.pos += d * 0.45
        self._draw()
        self._anim_job = self.after(16, self._step)

    def _draw(self):
        self.delete("all")
        w, h = self.W, self.H
        self.create_polygon(_rr_pts(0, 0, w, h, h / 2),
                            fill=GREEN if self.pos > 0.5 else "#E9E9EA",
                            outline=HAIR, smooth=True)
        kx = (h / 2) + self.pos * (w - h)     # 圆钮圆心 x
        self.create_oval(kx - h / 2 + 3, 3, kx + h / 2 - 3, h - 3,
                         fill="#FFFFFF", outline="#D9D9DE")


class GlassCard(tk.Frame):
    """玻璃卡片：圆角面 + 发丝边 + 底部软阴影。
    注意：画布上只画单个多边形——重叠多边形会触发 Tk canvas 的段错误。"""

    PAD = 14

    def __init__(self, parent):
        super().__init__(parent, bg=SHADOW, highlightthickness=0)
        self.cv = tk.Canvas(self, highlightthickness=0, bd=0, bg=BG)
        self.cv.pack(fill="both", expand=True, pady=(0, 3))   # 底边露 3px 阴影
        self.body = tk.Frame(self.cv, bg=CARD)
        self.win = self.cv.create_window(self.PAD, self.PAD, window=self.body,
                                         anchor="nw")
        self._last = None
        self.body.bind("<Configure>", self._on_body)
        self.bind("<Configure>", self._on_card)

    def _paint(self, w, h):
        if w < 24 or h < 24:      # 跳过早期几何来回
            return
        self.cv.delete("all")
        self.cv.create_polygon(_rr_pts(1, 1, w - 1, h - 1, 16), fill=CARD,
                               outline=HAIR)

    def _on_body(self, _):
        w = self.body.winfo_reqwidth() + 2 * self.PAD
        h = self.body.winfo_reqheight() + 2 * self.PAD + 3
        if (w, h) != self._last:
            self._last = (w, h)
            self.cv.configure(width=w, height=h)
            self._paint(w, h)

    def _on_card(self, e):
        self.cv.itemconfigure(self.win, width=max(1, e.width - 2 * self.PAD))
        self._paint(e.width, self.cv.winfo_height())


class Tooltip:
    def __init__(self, widget, text_fn):
        self.widget, self.text_fn, self.tip = widget, text_fn, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text_fn(), background="#1D1D1F", foreground="#F5F5F7",
                 font=("Segoe UI", 9), padx=10, pady=6, justify="left").pack()

    def _hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ---------------- 应用 ----------------


class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME)
        root.resizable(False, False)
        root.configure(background=BG)
        try:
            root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

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
        self._closing = False
        self._last_pos = (0, 0)
        self._coord_mismatch = 0
        self._rec_dirty = False
        self._ui_q = queue.Queue()

        # 语言 & 变量
        self.lang = default_lang()
        self.V = {}
        self._make_vars()
        self._load_persisted()
        self._wire_traces()

        self.shell = tk.Frame(root, background=BG)
        self.shell.pack(fill="both", expand=True)
        self._build()

        self._start_coord_polling()
        self._start_hotkeys()
        root.after(80, self._pump)
        root.after(60, lambda: apply_window_chrome(root, BG))
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- 变量 ----------
    def _make_vars(self):
        V = self.V
        V["pos_mode"] = tk.StringVar(value="follow")
        V["pos_x"] = tk.StringVar(value="0")
        V["pos_y"] = tk.StringVar(value="0")
        V["interval"] = tk.StringVar(value="200")
        V["unit"] = tk.StringVar(value="ms")
        V["jitter"] = tk.StringVar(value="50")
        V["human"] = tk.BooleanVar(value=True)
        V["pos_jitter"] = tk.StringVar(value="5")
        V["button"] = tk.StringVar(value="left")
        V["loops"] = tk.StringVar(value="0")
        V["speed"] = tk.StringVar(value="1.0")
        V["rec_jitter"] = tk.StringVar(value="30")
        V["rec_pos_jitter"] = tk.StringVar(value="5")
        V["rec_loops"] = tk.StringVar(value="1")
        V["rec_human"] = tk.BooleanVar(value=True)
        V["auto_load"] = tk.BooleanVar(value=True)
        # 常驻变量
        self.var_live_coords = tk.StringVar(value="")
        self.var_status = tk.StringVar(value="")
        self.var_pill = tk.StringVar(value="")
        self.var_rec_info = tk.StringVar(value="")
        self.var_preview = tk.StringVar(value="")
        self.var_btn_click = tk.StringVar(value="")
        self.var_btn_rec = tk.StringVar(value="")
        self.var_btn_play = tk.StringVar(value="")

    def _wire_traces(self):
        for name in ("interval", "jitter", "unit", "human"):
            self.V[name].trace_add("write", lambda *_: self._update_preview())
        self._update_preview()

    def tr(self, key):
        return TR[self.lang].get(key, TR["en"].get(key, key))

    def _settings_snapshot(self):
        return {k: v.get() for k, v in self.V.items()}

    def _apply_settings(self, data):
        for k, v in data.items():
            var = self.V.get(k)
            if var is None:
                continue
            if isinstance(var, tk.BooleanVar):
                var.set(bool(v))
            else:
                var.set(str(v))

    # ---------- 持久化 ----------
    def _persist_path(self):
        return config_file()

    def _load_persisted(self):
        try:
            with open(self._persist_path(), "r", encoding="utf-8") as fp:
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
            with open(self._persist_path(), "w", encoding="utf-8") as fp:
                json.dump({"app": APP_NAME, "version": CFG_VERSION,
                           "language": self.lang,
                           "settings": self._settings_snapshot()}, fp,
                          ensure_ascii=False, indent=1)
        except Exception:
            pass

    # ---------- 界面构建 ----------
    def _build(self):
        for w in self.shell.winfo_children():
            w.destroy()
        self._build_header()
        self.nb = ttk.Notebook(self.shell)
        self.nb.pack(fill="both", expand=True, padx=8)
        self.tab_clicker = ttk.Frame(self.nb)
        self.tab_record = ttk.Frame(self.nb)
        self.tab_settings = ttk.Frame(self.nb)
        self.tab_help = ttk.Frame(self.nb)
        self.nb.add(self.tab_clicker, text="  " + self.tr("tab_clicker") + "  ")
        self.nb.add(self.tab_record, text="  " + self.tr("tab_record") + "  ")
        self.nb.add(self.tab_settings, text="  " + self.tr("tab_settings") + "  ")
        self.nb.add(self.tab_help, text="  " + self.tr("tab_help") + "  ")
        self._build_clicker_tab(self.tab_clicker)
        self._build_record_tab(self.tab_record)
        self._build_settings_tab(self.tab_settings)
        self._build_help_tab(self.tab_help)
        self._build_statusbar()
        self.var_status.set(self.tr("status_ready"))
        self._update_preview()
        self._refresh_rec_info()

    def _card(self, parent, title_key):
        card = GlassCard(parent)
        card.pack(fill="x", padx=8, pady=(8, 0))
        if title_key:
            tk.Label(card.body, text=self.tr(title_key), bg=CARD, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        return card.body

    def _row(self, body):
        r = tk.Frame(body, bg=CARD)
        r.pack(fill="x", pady=3)
        return r

    def _lbl(self, parent, key, muted=False, sub=False):
        return tk.Label(parent, text=self.tr(key) if key else "",
                        bg=CARD, fg=MUTED if (muted or sub) else TEXT,
                        font=F_CAP if sub else F_BODY)

    def _build_header(self):
        hd = tk.Frame(self.shell, background=CARD, highlightthickness=0)
        hd.pack(fill="x")
        tk.Frame(hd, background=HAIR, height=1).pack(fill="x", side="bottom")
        inner = tk.Frame(hd, background=CARD)
        inner.pack(fill="x", padx=16, pady=10)
        left = tk.Frame(inner, background=CARD)
        left.pack(side="left")
        tk.Label(left, text=APP_NAME, background=CARD, foreground=TEXT,
                 font=F_TITLE).pack(anchor="w")
        tk.Label(left, textvariable=self.var_live_coords, background=CARD,
                 foreground=MUTED, font=F_CAP).pack(anchor="w")
        self.lang_seg_holder = tk.Frame(inner, background=CARD)
        self.lang_seg_holder.pack(side="right")
        seg = Segmented(self.lang_seg_holder,
                        [("zh", "中文"), ("en", "English")],
                        tk.StringVar(value=self.lang),
                        on_change=lambda v: self._switch_lang(v), height=28)
        seg.pack()
        vx, vy, vw, vh = virtual_screen()
        info = f"{vw}×{vh}"
        if (vx, vy) != (0, 0):
            info += f"  ({vx},{vy})"
        tk.Label(inner, text=info, background=CARD, foreground=MUTED,
                 font=F_CAP).pack(side="right", padx=12)

    def _build_clicker_tab(self, tab):
        b1 = self._card(tab, "target")
        r = self._row(b1)
        Segmented(r, [("follow", self.tr("pos_mode_follow")),
                      ("fixed", self.tr("pos_mode_fixed"))],
                  self.V["pos_mode"], height=30).pack(side="left")
        pick = tk.Frame(r, bg=CARD)
        pick.pack(side="right")
        Pill(pick, tk.StringVar(value="◈ " + self.tr("pick_current")),
             command=self._use_current_pos, kind="secondary", height=30,
             padx=12, font=F_BODY).pack()

        r2 = self._row(b1)
        self._lbl(r2, "x").pack(side="left")
        ttk.Entry(r2, textvariable=self.V["pos_x"], width=8,
                  style="Field.TEntry").pack(side="left", padx=(6, 10))
        self._lbl(r2, "y").pack(side="left")
        ttk.Entry(r2, textvariable=self.V["pos_y"], width=8,
                  style="Field.TEntry").pack(side="left", padx=6)

        b2 = self._card(tab, "timing")
        r = self._row(b2)
        self._lbl(r, "interval").pack(side="left")
        e = ttk.Entry(r, textvariable=self.V["interval"], width=9,
                      style="Field.TEntry")
        e.pack(side="left", padx=(8, 8))
        Tooltip(e, lambda: self.tr("tip_interval"))
        Segmented(r, [("ms", "ms"), ("s", "s")], self.V["unit"], height=26).pack(side="left")
        r2 = self._row(b2)
        self._lbl(r2, "jitter").pack(side="left")
        e = ttk.Entry(r2, textvariable=self.V["jitter"], width=9,
                      style="Field.TEntry")
        e.pack(side="left", padx=(8, 8))
        Tooltip(e, lambda: self.tr("tip_jitter"))
        self._lbl(r2, "same_unit", muted=True).pack(side="left")
        r3 = self._row(b2)
        Switch(r3, self.V["human"]).pack(side="left")
        hb = tk.Frame(r3, bg=CARD)
        hb.pack(side="left", padx=(10, 0))
        tk.Label(hb, text=self.tr("human"), bg=CARD, fg=TEXT, font=F_BOLD).pack(anchor="w")
        tk.Label(hb, text=self.tr("human_sub"), bg=CARD, fg=MUTED, font=F_CAP).pack(anchor="w")
        Tooltip(r3, lambda: self.tr("tip_human"))
        tk.Label(b2, textvariable=self.var_preview, bg=CARD, fg=MUTED,
                 font=F_CAP).pack(anchor="w", pady=(4, 0))

        b3 = self._card(tab, "behavior")
        r = self._row(b3)
        self._lbl(r, "pos_jitter").pack(side="left")
        e = ttk.Entry(r, textvariable=self.V["pos_jitter"], width=6,
                      style="Field.TEntry")
        e.pack(side="left", padx=(8, 0))
        Tooltip(e, lambda: self.tr("tip_posj"))
        self._lbl(r, "mouse_button").pack(side="left", padx=(20, 6))
        Segmented(r, [("left", self.tr("left")), ("right", self.tr("right"))],
                  self.V["button"], height=26).pack(side="left")
        r2 = self._row(b3)
        self._lbl(r2, "loops").pack(side="left")
        ttk.Entry(r2, textvariable=self.V["loops"], width=6,
                  style="Field.TEntry").pack(side="left", padx=(8, 6))
        self._lbl(r2, "loops_unit", muted=True).pack(side="left")

        self.btn_click = Pill(tab, self.var_btn_click, command=self.toggle_clicker,
                              kind="primary", height=46, font=("Segoe UI", 12, "bold"))
        self.btn_click.pack(fill="x", padx=10, pady=14)

    def _build_record_tab(self, tab):
        bar = tk.Frame(tab, background=BG)
        bar.pack(fill="x", padx=8, pady=(8, 0))
        self.btn_rec = Pill(bar, self.var_btn_rec, command=self.toggle_record,
                            kind="primary", height=36)
        self.btn_rec.pack(side="left")
        self.btn_play = Pill(bar, self.var_btn_play, command=self.toggle_play,
                             kind="primary", height=36)
        self.btn_play.pack(side="left", padx=(8, 0))
        Pill(bar, tk.StringVar(value=self.tr("clear")), command=self._clear_rec,
             kind="secondary", height=36).pack(side="left", padx=(8, 0))
        Pill(bar, tk.StringVar(value=self.tr("save_script")), command=self._save_script,
             kind="secondary", height=36).pack(side="right")
        Pill(bar, tk.StringVar(value=self.tr("load_script")), command=self._load_script,
             kind="secondary", height=36).pack(side="right", padx=(0, 8))

        b1 = self._card(tab, "rec_card")
        tk.Label(b1, textvariable=self.var_rec_info, bg=CARD, fg=TEXT,
                 font=F_BOLD).pack(anchor="w")

        b2 = self._card(tab, "play_card")
        rows = [("speed", "speed", "tip_speed"),
                ("rec_jitter", "rec_jitter", None),
                ("rec_pos_jitter", "rec_pos_jitter", None),
                ("rec_loops", "rec_loops", None)]
        for key, var, tip in rows:
            r = self._row(b2)
            self._lbl(r, key).pack(side="left")
            e = ttk.Entry(r, textvariable=self.V[var], width=8, style="Field.TEntry")
            e.pack(side="left", padx=(8, 0))
            if tip:
                Tooltip(e, lambda t=tip: self.tr(t))
        r = self._row(b2)
        Switch(r, self.V["rec_human"]).pack(side="left")
        self._lbl(r, "rec_human").pack(side="left", padx=(10, 0))
        Tooltip(r, lambda: self.tr("tip_human"))
        tk.Frame(b2, bg=CARD, height=4).pack()

    def _build_settings_tab(self, tab):
        b1 = self._card(tab, "general")
        r = self._row(b1)
        self._lbl(r, "language").pack(side="left")
        Segmented(r, [("zh", "中文"), ("en", "English")],
                  tk.StringVar(value=self.lang),
                  on_change=lambda v: self._switch_lang(v), height=28).pack(side="right")
        tk.Frame(b1, bg=HAIR, height=1).pack(fill="x", pady=7)
        r = self._row(b1)
        self._lbl(r, "auto_load").pack(side="left")
        Switch(r, self.V["auto_load"]).pack(side="right")

        b2 = self._card(tab, "cfg_card")
        r = self._row(b2)
        Pill(r, tk.StringVar(value="⭳ " + self.tr("export_cfg")),
             command=self._export_cfg, kind="primary", height=32, font=F_BODY).pack(side="right")
        Pill(r, tk.StringVar(value="⭱ " + self.tr("import_cfg")),
             command=self._import_cfg, kind="primary", height=32, font=F_BODY).pack(side="right", padx=(0, 8))
        tk.Label(b2, text=self.tr("cfg_note"), bg=CARD, fg=MUTED, font=F_CAP,
                 wraplength=520, justify="left").pack(anchor="w", pady=(2, 0))

        b3 = self._card(tab, "about")
        tk.Label(b3, text=f"{APP_NAME} · v3.0 · Windows 10/11", bg=CARD,
                 fg=MUTED, font=F_CAP).pack(anchor="w")
        tk.Label(b3, text="SendInput · pynput · Tkinter — F6 / F8 / F9", bg=CARD,
                 fg=MUTED, font=F_CAP).pack(anchor="w")

    def _build_help_tab(self, tab):
        txt = ScrolledText(tab, wrap="word", font=("Segoe UI", 10), background=CARD,
                           foreground=TEXT, relief="flat", padx=18, pady=14,
                           highlightthickness=0)
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", HELP_TEXT[self.lang])
        txt.configure(state="disabled")

    def _build_statusbar(self):
        bar = tk.Frame(self.shell, background=BG)
        bar.pack(fill="x", side="bottom", padx=14, pady=(4, 12))
        self.state_lbl = tk.Label(bar, textvariable=self.var_pill, background=MUTED,
                                  foreground="#FFFFFF", font=("Segoe UI", 9, "bold"),
                                  padx=11, pady=3)
        self.state_lbl.pack(side="left")
        ttk.Label(bar, textvariable=self.var_status, style="Muted.TLabel").pack(
            side="left", padx=(10, 0))
        tk.Label(bar, text="F6 · F8 · F9", background=BG, foreground=MUTED,
                 font=F_CAP).pack(side="right")

    def _switch_lang(self, lang):
        if lang == self.lang:
            return
        self.lang = lang
        self._build()

    # ---------- 事件泵 ----------
    def _pump(self):
        if self._closing:
            return
        try:
            while True:
                self._ui_q.get_nowait()()
        except queue.Empty:
            pass
        x, y = self._last_pos
        self.var_live_coords.set(f"●  mouseX ({x}, {y})")
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
            state, color = self.tr("state_idle"), MUTED
        self.var_pill.set("● " + state)
        try:
            self.state_lbl.configure(background=color)
        except tk.TclError:
            pass
        self.var_btn_click.set(self.tr("stop_click") if self.clicking else self.tr("start"))
        self.var_btn_rec.set(self.tr("stop_rec") if self.recording else self.tr("record"))
        self.var_btn_play.set(self.tr("stop_play") if self.playing else self.tr("play"))
        try:
            self.btn_click.set_kind("danger" if self.clicking else "primary")
            self.btn_rec.set_kind("danger" if self.recording else "primary")
            self.btn_play.set_kind("danger" if self.playing else "primary")
        except AttributeError:
            pass
        self.root.after(80, self._pump)

    def _set_status(self, s):
        self._ui_q.put(lambda s=s: self.var_status.set(s))

    # ---------- 参数读取 ----------
    def _get_float(self, var, default=0.0):
        try:
            return float(var.get())
        except ValueError:
            return default

    def _get_int(self, var, default=0):
        try:
            return int(float(var.get()))
        except ValueError:
            return default

    def _interval_ms(self):
        mult = 1000.0 if self.V["unit"].get() == "s" else 1.0
        interval = self._get_float(self.V["interval"], 200) * mult
        jitter = max(0.0, self._get_float(self.V["jitter"], 0) * mult)
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
        x, y = self._last_pos
        self.V["pos_mode"].set("fixed")
        self.V["pos_x"].set(str(x))
        self.V["pos_y"].set(str(y))
        self._set_status(self.tr("pick_ok").format(x=x, y=y))

    def _start_coord_polling(self):
        def poll():
            while not self._closing:
                try:
                    self._last_pos = cursor_pos()
                except Exception:
                    pass
                time.sleep(0.1)
        threading.Thread(target=poll, daemon=True).start()

    # ---------- 连点 ----------
    def toggle_clicker(self):
        if self.clicking:
            self.clicker_stop.set()
            return
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
        fixed = V["pos_mode"].get() == "fixed"
        fx = self._get_int(V["pos_x"], 0)
        fy = self._get_int(V["pos_y"], 0)
        human = V["human"].get()

        self.clicking = True
        n = 0
        while not stop.is_set() and (loops == 0 or n < loops):
            if fixed:
                x, y = fx, fy
            else:
                x, y = cursor_pos()
            dx, dy = human_offset(pos_j, human)
            do_click(x + dx, y + dy, btn)
            n += 1
            self._set_status(self.tr("clicking").format(n=n))
            stop.wait(human_interval_ms(interval, jitter, human))
        self.clicking = False
        self._set_status(self.tr("click_done").format(n=n))

    # ---------- 录制 ----------
    def toggle_record(self):
        if self.playing:
            messagebox.showinfo(APP_NAME, self.tr("need_stop_play"))
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
        self._refresh_rec_info()

    def _rec_counts(self):
        c = sum(1 for e in self.recorded if e.get("type") in ("down", "click"))
        m = sum(1 for e in self.recorded if e.get("type") == "move")
        return c, m

    def _refresh_rec_info(self):
        c, m = self._rec_counts()
        if self.recording:
            check = self.tr("rec_ok") if self._coord_mismatch <= 3 \
                else self.tr("rec_bad").format(n=self._coord_mismatch)
            self.var_rec_info.set(self.tr("rec_info_fmt").format(c=c, m=m, check=check))
        elif c == 0 and m == 0:
            self.var_rec_info.set(self.tr("rec_none"))
        else:
            check = self.tr("rec_ok") if self._coord_mismatch <= 3 \
                else self.tr("rec_bad").format(n=self._coord_mismatch)
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
            messagebox.showinfo(APP_NAME, self.tr("need_stop_rec"))
            return
        if self.playing:
            self.play_stop.set()
            return
        if not self.recorded:
            messagebox.showinfo(APP_NAME, self.tr("need_record"))
            return
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

        self.playing = True
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
                if wait > 0 and stop.wait(wait):
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
            messagebox.showinfo(APP_NAME, self.tr("need_stop_save"))
            return
        if not self.recorded:
            messagebox.showinfo(APP_NAME, self.tr("nothing_saved"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")],
                                            initialfile="script.json")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(self.recorded, fp, ensure_ascii=False, indent=1)
        self._set_status(self.tr("saved_to").format(p=path))

    def _load_script(self):
        if self.recording or self.playing:
            messagebox.showinfo(APP_NAME, self.tr("nothing_loaded"))
            return
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
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
            messagebox.showerror(self.tr("load_fail"), str(e))

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

    # ---------- 配置导入/导出 ----------
    def _export_cfg(self):
        if self.recording:
            messagebox.showinfo(APP_NAME, self.tr("need_stop_save"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")],
                                            initialfile="autoclicker_profile.json")
        if not path:
            return
        data = {"app": APP_NAME, "version": CFG_VERSION, "language": self.lang,
                "settings": self._settings_snapshot(), "script": self.recorded}
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=1)
        self._set_status(self.tr("cfg_saved").format(p=path))

    def _import_cfg(self):
        if self.recording or self.playing:
            messagebox.showinfo(APP_NAME, self.tr("nothing_loaded"))
            return
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
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
            if data.get("language") in ("zh", "en"):
                self.lang = data["language"]
            self._build()
            self._refresh_rec_info()
            self._set_status(self.tr("cfg_loaded").format(p=path))
        except Exception as e:
            messagebox.showerror(self.tr("cfg_fail"), str(e))

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

    def _on_close(self):
        self._closing = True
        self.clicker_stop.set()
        self.play_stop.set()
        self.recording = False
        self._save_persisted()
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
            if self.kb_listener:
                self.kb_listener.stop()
        finally:
            self.root.destroy()


def setup_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", background=BG, foreground=TEXT, font=F_BODY)
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(10, 2, 0, 0))
    style.configure("TNotebook.Tab", padding=(18, 9), font=("Segoe UI", 10, "bold"),
                    background=BG, foreground=MUTED, borderwidth=0)
    style.map("TNotebook.Tab",
              foreground=[("selected", TEXT)],
              background=[("selected", BG)])
    style.configure("Muted.TLabel", background=BG, foreground=MUTED)
    style.configure("Field.TEntry", fieldbackground=FIELD, foreground=TEXT,
                    borderwidth=0, padding=6, insertcolor=TEXT)
    style.map("Field.TEntry", fieldbackground=[("focus", "#FFFFFF")])
    style.configure("TEntry", fieldbackground=FIELD, borderwidth=0, padding=6)


if __name__ == "__main__":
    enable_dpi_awareness()
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", user32.GetDpiForSystem() / 72.0)
    except Exception:
        pass
    setup_theme(root)
    App(root)
    root.mainloop()
