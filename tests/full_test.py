# -*- coding: utf-8 -*-
"""AutoClicker Pro 全量功能回归测试（offscreen，不干扰真实窗口）"""
import importlib.util, os, tempfile, random, time, threading

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AC_TEST"] = "1"

D = tempfile.mkdtemp(prefix="ac_full_test_")
PASSED, FAILED = [], []

def section(name):
    print(f"\n== {name} ==")

def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (f"  [{detail}]" if detail and not cond else ""))

import threading as _th
def _hook(args):
    print(f"  !! 线程异常: {args.exc_type.__name__}: {args.exc_value}", flush=True)
_th.excepthook = _hook
spec = importlib.util.spec_from_file_location('ck', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'clicker.py'))
ck = importlib.util.module_from_spec(spec)
ck.__name__ = 'ck'
spec.loader.exec_module(ck)
ck.config_file = lambda n="autoclicker_config.json": os.path.join(D, n)

from PySide6.QtWidgets import QApplication, QMessageBox
qapp = QApplication([])
ck.QMessageBox.exec = staticmethod(lambda self: None)          # 弹窗不阻塞
ck.QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

app = ck.App()

# 测试专用：App 内部创建的连点/回放线程改为同步内联执行（确定性强）
import threading as _rt
class InlineThread(_rt.Thread):
    def start(self):
        # 轮询线程无限循环，仍用真实线程；连点/回放为有限循环，同步内联
        if getattr(self._target, "__name__", "") == "poll":
            return super().start()
        if self._target:
            self._target(*self._args, **self._kwargs)
    def join(self, timeout=None):
        pass
ck.threading.Thread = InlineThread

def run_clicker(expect=None):
    before = len(calls)
    app.toggle_clicker()          # 内联同步：返回即循环已结束
    if expect is not None and len(calls) - before != expect:
        print(f"  [dbg] 预期 {expect} 实际 {len(calls) - before}")

# ============ 1. 间隔与单位 ============
section("1. 间隔与抖动单位换算")
app.V["interval"].set("200"); app.V["unit"].set("ms")
app.V["jitter"].set("50");   app.V["jitter_unit"].set("ms")
check("ms/ms 基础换算", app._interval_ms() == (200.0, 50.0))
app.V["interval"].set("5"); app.V["unit"].set("s")
app.V["jitter"].set("100"); app.V["jitter_unit"].set("ms")
check("间隔 s + 抖动 ms", app._interval_ms() == (5000.0, 100.0))
app.V["interval"].set("0.2"); app.V["unit"].set("s")
app.V["jitter"].set("0.05"); app.V["jitter_unit"].set("s")
check("间隔 s + 抖动 s", app._interval_ms() == (200.0, 50.0))
check("预览文本随单位刷新", ("200ms" in app.var_preview.get()))

# ============ 2. 拟人化分布 ============
section("2. 拟人化分布")
random.seed(7)
vals = [ck.human_interval_ms(5000, 1000, True) for _ in range(5000)]
mean = sum(vals) / len(vals)
check("高斯均值接近中心(5s)", 4900 <= mean * 1000 <= 5100, f"{mean*1000:.0f}ms")
check("间隔钳制在 ±抖动(+走神)内", 3999 <= min(vals)*1000 and max(vals)*1000 <= 6360)
walk = sum(1 for v in vals if v * 1000 > 5080)
check("存在走神停顿", walk > 50, f"{walk}/5000")
uni = [ck.human_interval_ms(5000, 1000, False) for _ in range(2000)]
check("非拟人=±抖动均匀随机", all(4.0 <= v <= 6.0 for v in uni))
offs = [ck.human_offset(10, True) for _ in range(3000)]
center = sum(1 for dx, dy in offs if abs(dx) <= 5 and abs(dy) <= 5)
check("位置偏移高斯(中心密集)", center / 3000 >= 0.45, f"{center/3000:.0%}")
check("位置偏移不出界", all(abs(dx) <= 10 and abs(dy) <= 10 for dx, dy in offs))

# ============ 3. 连点三模式 ============
import traceback as _tb
_orig_evt_set = _th.Event.set
def _dbg_set(self):
    try:
        if self is getattr(app, "clicker_stop", None) and app.clicking:
            stack = "".join(_tb.format_stack()[-8:-1])
            nl = chr(10)
        print("!! clicker_stop.set() 调用栈:" + nl + stack, flush=True)
    except Exception:
        pass
    _orig_evt_set(self)
_th.Event.set = _dbg_set


section("3. 连点三模式")
calls = []
ck.do_click = lambda x, y, b="left": calls.append((x, y, b))
ck.send_move = lambda x, y: calls.append(("mv", x, y))
ck.send_button = lambda b, d: calls.append(("dn" if d else "up", b))
ck.cursor_pos = lambda: (777, 888)
app.V["unit"].set("ms"); app.V["jitter_unit"].set("ms")   # 复位单位（第1节会遗留 s）
app.V["jitter"].set("0"); app.V["pos_jitter"].set("0")
app.V["human"].set(False); app.V["click_action"].set("single")
app.V["button"].set("left")

app.V["pos_mode"].set("fixed"); app.V["pos_x"].set("100"); app.V["pos_y"].set("200")
app.V["loops"].set("3"); app.V["interval"].set("10")
run_clicker(expect=3)
check("固定坐标 3 次", calls == [(100, 200, "left")] * 3, str(calls))

calls.clear(); app.V["pos_mode"].set("follow"); app.V["loops"].set("2")
run_clicker(expect=2)
check("跟随鼠标取当前位置", calls == [(777, 888, "left")] * 2, str(calls))

calls.clear()
app.V["pos_mode"].set("multi"); app.V["points"].set([[1, 1], [2, 2], [3, 3]])
app.V["loops"].set("2")   # 2 轮 × 3 点
run_clicker(expect=6)
check("多点循环 2 轮顺序正确", calls == [(1, 1, "left"), (2, 2, "left"), (3, 3, "left")] * 2, str(calls))

calls.clear(); app.V["pos_mode"].set("fixed"); app.V["button"].set("right"); app.V["loops"].set("1")
run_clicker(expect=1)
check("右键点击", calls == [(100, 200, "right")], str(calls))
app.V["button"].set("left")

app.V["points"].set([]); calls.clear()
app.toggle_clicker()
check("空列表拦截且不启动", not app.clicking)

# ============ 4. 点击动作 ============
section("4. 点击动作：双击 / 拖动")
app.V["pos_mode"].set("fixed"); app.V["pos_x"].set("50"); app.V["pos_y"].set("60")
app.V["loops"].set("1"); app.V["interval"].set("10")

calls.clear(); app.V["click_action"].set("double")
run_clicker(expect=2)
check("双击=同点位两次点击", calls.count((50, 60, "left")) == 2, str(calls))

calls.clear(); app.V["click_action"].set("drag")
run_clicker(expect=1)
dns = calls.count(("dn", "left")); ups = calls.count(("up", "left"))
mvs = [c for c in calls if c[0] == "mv"]
check("拖动=按下+抬起成对", dns == 1 and ups == 1)
check("拖动有移动轨迹", len(mvs) >= 2, str(len(mvs)))

calls.clear()
app.V["pos_mode"].set("multi"); app.V["points"].set([[0, 0], [100, 100]])
app.V["loops"].set("1")
run_clicker(expect=2)
dns = calls.count(("dn", "left")); ups = calls.count(("up", "left"))
check("多点拖动 2 段(A→B、B→A)", dns == 2 and ups == 2, f"dn={dns} up={ups}")
mvs = [(c[1], c[2]) for c in calls if c[0] == "mv"]
check("拖动经过起点与终点", (0, 0) in mvs and (100, 100) in mvs)

# ============ 5. 录制 ============
section("5. 录制")
app._last_rec_move = (0, 0, 0.0)
app.rec_start = time.perf_counter()
app.recording = True
app._on_rec_move(100, 100)
time.sleep(0.05)
app._on_rec_click(150, 160, type("B", (), {"name": "left"})(), True)
app._on_rec_click(150, 160, type("B", (), {"name": "left"})(), False)
for i in range(3):
    app._on_rec_move(200 + i, 200 + i)
time.sleep(0.05)
app._on_rec_click(210, 210, type("B", (), {"name": "right"})(), True)
app._on_rec_click(210, 210, type("B", (), {"name": "right"})(), False)
app.recording = False
c, m = app._rec_counts()
check("录制点击/移动计数(移动40ms节流)", c == 2 and m >= 2, f"c={c} m={m}")
types = [e["type"] for e in app.recorded]
check("按下抬起成对记录", types.count("down") == 2 and types.count("up") == 2)

# ============ 6. 回放 ============
section("6. 回放")
calls.clear()
app.V["speed"].set("8"); app.V["rec_jitter"].set("0")
app.V["rec_pos_jitter"].set("0"); app.V["rec_human"].set(False)
app.V["rec_loops"].set("1")
app.toggle_play()              # 内联同步执行
dns = calls.count(("dn", "left")) + calls.count(("dn", "right"))
ups = calls.count(("up", "left")) + calls.count(("up", "right"))
check("回放按下/抬起成对", dns == 2 and ups == 2, f"dn={dns} up={ups}")
check("回放有移动轨迹", len([c for c in calls if c[0] == "mv"]) >= 5)

# ============ 7. 双击对识别 ============
section("7. 双击对识别与保护")
rec = [{"t": 0.10, "type": "down", "x": 500, "y": 500, "button": "left"},
       {"t": 0.14, "type": "up", "x": 500, "y": 500, "button": "left"},
       {"t": 0.25, "type": "down", "x": 502, "y": 501, "button": "left"},
       {"t": 0.29, "type": "up", "x": 502, "y": 501, "button": "left"},
       {"t": 0.90, "type": "down", "x": 500, "y": 500, "button": "left"},
       {"t": 0.94, "type": "up", "x": 500, "y": 500, "button": "left"},
       {"t": 1.00, "type": "down", "x": 800, "y": 800, "button": "left"},
       {"t": 1.04, "type": "up", "x": 800, "y": 800, "button": "left"}]
pairs, spans = ck.detect_double_clicks(rec)
check("双击对识别", pairs == {2: 0}, str(pairs))
check("非双击不误判", 4 not in pairs and 6 not in pairs)

# ============ 8. 脚本库 ============
section("8. 脚本库")
import PySide6.QtWidgets as qw
qw.QInputDialog.getText = staticmethod(lambda *a, **k: ("测试脚本A", True))
app.recorded = [{"t": 0.1, "type": "click", "x": 1, "y": 1, "button": "left"}]
app._lib_save()
app.recorded = [{"t": 0.2, "type": "click", "x": 2, "y": 2, "button": "right"}]
qw.QInputDialog.getText = staticmethod(lambda *a, **k: ("测试脚本B", True))
app._lib_save()
check("两个命名脚本入库", set(app.library) == {"测试脚本A", "测试脚本B"})
app.lib_combo.setCurrentText("测试脚本A"); qapp.processEvents()
check("下拉切换自动加载 A", app.recorded[0]["x"] == 1)
app.lib_combo.setCurrentText("测试脚本B"); qapp.processEvents()
check("下拉切换自动加载 B", app.recorded[0]["x"] == 2)
app._lib_del()
check("删除脚本 B", "测试脚本B" not in app.library and "测试脚本A" in app.library)
app3 = ck.App()
check("脚本库持久化", "测试脚本A" in app3.library)
app3.close(); app._lib_refresh()

# ============ 9. 旧格式兼容 ============
section("9. 旧格式兼容")
norm = app._normalize_events([{"t": 1.0, "x": 5, "y": 6, "button": "right"},
                              {"t": 2.0, "type": "move", "x": 7, "y": 8}])
check("旧格式自动升级", norm[0]["type"] == "click" and norm[1]["type"] == "move")

# ============ 10. 配置持久化 ============
section("10. 配置持久化")
app.V["interval"].set("333"); app.V["unit"].set("ms")
app.V["pos_mode"].set("multi"); app.V["points"].set([[9, 9], [8, 8]])
app.V["theme"].set("dark")
app._save_persisted()
app2 = ck.App()
check("参数持久化", app2.V["interval"].get() == "333")
check("点位持久化", app2.V["points"].get() == [[9, 9], [8, 8]])
check("主题持久化", app2.V["theme"].get() == "dark")

# ============ 11. 双语 / 主题 ============
section("11. 双语与主题")
app._switch_lang("en")
check("英文界面", "Clicker" in app.tabs.tabText(0))
app.V["interval"].set("333")
app._switch_lang("zh")
check("切换后设置保留", app.V["interval"].get() == "333")
check("中文界面", "自动连点" in app.tabs.tabText(0))
app._switch_theme("dark"); qapp.processEvents()
check("深色主题生效", ck.CUR["BG"] == "#1E1F24")
app._switch_theme("light"); qapp.processEvents()
check("浅色主题生效", ck.CUR["BG"] == "#F2F3F7")

# ============ 12. 紧急停止 ============
section("12. 紧急停止")
ck.cursor_pos = lambda: (0, 0)
app.clicking = True                        # 模拟连点运行中
app._last_pos = (0, 0); app._corner_armed = True
app._poll_once()                           # 单次轮询：应入队紧急停止
qapp.processEvents()
while not app._ui_q.empty():
    app._ui_q.get_nowait()()
check("角落急停生效(停止信号已发出)", app.clicker_stop.is_set())
app.clicking = True; app._last_pos = (999, 999); app._corner_armed = True
app._poll_once()
while not app._ui_q.empty(): app._ui_q.get_nowait()()
check("非角落不误触发", app.clicking)
app.clicking = False

# ============ 13. 托盘与关闭 ============
section("13. 托盘与关闭行为")
check("托盘已创建", app.tray is not None)
check("托盘菜单存在", app.tray.contextMenu() is not None)
app.V["close_to_tray"].set(True); app._quit = False
app.close()
check("关闭隐藏到托盘", not app.isVisible() and not app._quit)
app._quit = True; app.close()

# ============ 汇总 ============
print(f"\n== 结果: {len(PASSED)} 通过 / {len(FAILED)} 失败 ==")
if FAILED:
    print("失败项:")
    for f in FAILED:
        print("  [FAIL]", f)
raise SystemExit(1 if FAILED else 0)
