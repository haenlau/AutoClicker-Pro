# AutoClicker Pro — 项目交接文档

> 给接手本项目的 AI / 开发者：本文档足以在 10 分钟内理解项目全貌。
> 当前版本 v4.6 · 全量回归测试 45/45 通过 · 已上传 GitHub（Releases 提供打包 exe）。

## 一、这是什么

Windows 桌面鼠标自动化工具（Python + PySide6/Qt）：

- **自动连点**三种模式：跟随鼠标 / 固定坐标（3 秒倒计时拾取）/ 多点循环（坐标列表按顺序轮流）
- **完整宏录制回放**：移动轨迹 + 按下/抬起（支持拖动、双击），时间轴精确重放
- **拟人化防检测**：高斯分布间隔、5% 概率"走神"停顿、高斯位置偏移、随机按下时长
- **点击动作**：单击 / 双击 / 拖动（多点循环下为 A→B→C 连拖）
- **脚本库**：命名保存多个录制脚本，下拉即切换；配置导入/导出（含脚本）
- **系统托盘**：关闭最小化到托盘，托盘菜单控制一切
- **紧急停止**：运行中鼠标甩到屏幕左上角，所有动作立即停止
- **全局热键**：F6 连点 · F8 录制 · F9 回放（任何窗口下有效，触发自动跳转对应页）
- 中英双语（跟随系统语言）+ 浅色/深色主题 + 设置自动持久化

## 二、文件结构

```
clicker.py            全部源码（单文件，约 2000 行）
clicker_tk_backup.py  旧 Tkinter 版备份（已弃用，仅存档）
gen_icon.py           图标生成脚本（Pillow 绘制，输出 icon.ico/icon.png）
icon.ico / icon.png   应用图标（打包时经 --add-data 嵌入 exe）
tests/full_test.py    全量功能回归测试（45 项断言，offscreen 无头运行）
tests/run.log         最近一次测试输出
AutoClicker.spec      PyInstaller 打包配置
dist/AutoClicker.exe  打包产物（约 46MB，单文件）
dist/鼠标连点器.exe    同上副本（中文文件名）
```

## 三、运行 / 测试 / 打包

```bash
pip install PySide6 pynput pillow pyinstaller

# 开发运行
python clicker.py

# 全量回归测试（无头，不弹窗不干扰桌面；必须带 AC_TEST=1）
AC_TEST=1 PYTHONUNBUFFERED=1 python tests/full_test.py

# 打包单文件 exe
pyinstaller --noconfirm --onefile --windowed --clean \
  --icon=icon.ico --add-data "icon.ico;." \
  --name=AutoClicker clicker.py

# 重新生成图标（改设计时）
python gen_icon.py
```

## 四、技术架构（5 分钟版）

- **UI**：PySide6。QSS 全局样式表（浅色/深色两套主题色，见 `THEMES` 字典与
  `make_qss()`）。自绘控件：`Segmented`（iOS 分段控制器）、`Switch`（拨动开关）、
  `Pill`（药丸按钮）。窗口经 DWM API 做原生圆角 + 标题栏融色（`apply_window_chrome`）。
- **状态管理**：自制 `Var` 类（可观察变量，get/set + 回调），界面控件与逻辑共享。
  所有设置项都在 `app.V` 字典里，快照/恢复/导入导出都遍历它。
- **点击注入**：`ctypes` 直调 `user32.SendInput`（绝对坐标按虚拟桌面归一化）。
- **录制**：`pynput.mouse.Listener` 全局钩子；移动按 40ms 节流采样。
- **全局热键**：`pynput.keyboard.GlobalHotKeys`（F6/F8/F9）。
- **线程模型（重要）**：钩子/轮询线程只写数据结构和标志位，一切界面更新经
  `app._ui_q` 队列，由主线程 QTimer(80ms) 的 `_pump()` 统一执行。
  **任何工作线程不得直接触碰 Qt 控件。**
- **等待机制**：连点/回放/拖动的所有等待用 **time.sleep 轮询 + stop 标志检查**，
  不用 `Event.wait(timeout)`（见"历史坑"第 1 条）。
- **持久化**：`config_file()` 定位 `autoclicker_config.json`（设置）与
  `autoclicker_scripts.json`（脚本库），优先 exe/脚本所在目录，失败退到 %APPDATA%。
- **DPI/RDP**：依赖 Qt 自身的 Per-Monitor DPI 感知；已实测 RDP 无屏机场景可用。

## 五、历史坑（改代码前必读，都是真实踩过的）

1. **不要用 `Event.wait(timeout)` 做可中断等待**——在此环境（offscreen/Qt +
   RDP）会偶发单次等待不唤醒，线程卡死数秒到数十秒。已全部换成
   `while time.time() < deadline and not stop: sleep(0.005)` 轮询。
2. **`toggle_clicker/toggle_play` 里的 `clicking/playing = True` 必须在
   `toggle` 函数内同步置位**（不能等线程内部置位），否则快速重复触发
   （如连按 F6）会启动多个并发点击线程。线程退出时复位状态。
3. **测试必须设置环境变量 `AC_TEST=1`**：`_msg()` 样式弹窗和删除确认框会检查
   它来跳过模态 `exec()`，否则无头测试会卡死在弹窗上。
4. **测试里 `ck.threading.Thread` 被替换为 `InlineThread`**（连点/回放循环
   同步内联执行，确定性强），但 target 名为 `poll` 的线程例外——仍走真实
   线程（无限轮询循环，内联会卡死）。别把这个例外改掉。
5. **录制钩子回调（`_on_rec_click/_on_rec_move`）必须极快且绝不抛异常**：
   pynput 的回调抛异常会静默停掉监听；回调慢了 Windows 会丢低级钩子事件
   （快速双击丢失就是这个原因）。界面更新只置 `_rec_dirty` 脏标记。
6. 多点循环的"循环次数"语义 = **完整轮数**（2 点 × 2 轮 = 4 次点击）。
7. 双击对（`detect_double_clicks`）：回放时两次点击共用同一位置偏移、
   间隔钳制在系统双击时限内，否则双击会被回放拆散成两次单击。
8. 若回退到旧 Tkinter 版（不推荐）：Tk 画布 smooth 多边形 + 重叠多边形
   会段错误；QMessageBox... 与 Qt 无关，仅存档提醒。

## 六、测试覆盖（45 项）

间隔单位换算(4) / 拟人分布(6) / 连点三模式+右键+空列表拦截(6) /
点击动作：双击·拖动·多点拖动(5) / 录制(2) / 回放(2) / 双击对识别(2) /
脚本库增删切换持久化(4) / 旧格式兼容(1) / 配置持久化(3) / 双语主题(5) /
紧急停止(2) / 托盘与关闭(2)。

运行方式见"三"。失败时日志在 tests/run.log；线程异常会以
`!! 线程异常: ...` 打印（测试里挂了 `threading.excepthook`）。

## 七、上传 GitHub 建议

1. **包含**：clicker.py、tests/full_test.py、gen_icon.py、icon.ico/icon.png、
   AutoClicker.spec、clicker_tk_backup.py（可选）、本文档。
2. **排除**（建议加 .gitignore）：`dist/`、`build/`、`__pycache__/`、
   `*.log`、`autoclicker_config.json`、`autoclicker_scripts.json`
   （后两个含用户个人配置与脚本，属用户数据）。
3. 仓库根目录建议补一个面向用户的 README.md（功能截图 + 下载链接指向
   Releases 的 exe），开发交接看本文档即可。
4. 注意：PyInstaller 单文件 exe 约 46MB，建议走 GitHub Releases 而非仓库本体。
5. 免责声明建议：工具仅供个人自动化使用，使用于游戏等场景请遵守目标平台条款。

## 八、已知限制与后续方向（按价值排序）

- 定时任务（定时启动/到时停止）——挂机场景的自然下一步
- 脚本步骤编辑器（删除误触步骤、单步调速、分段试跑）
- 找色/找图点击（截图确认目标出现才点；需引入图像匹配，工作量最大）
- 代码签名（消除杀软误报；需证书）

## 九、当前设置项清单（app.V 键名）

pos_mode(follow/fixed/multi) · pos_x/pos_y · interval+unit · jitter+jitter_unit ·
human · click_action(single/double/drag) · pos_jitter · button(left/right) ·
loops · speed · rec_jitter · rec_pos_jitter · rec_loops · rec_human ·
auto_load · theme(light/dark) · points([[x,y],...]) · corner_stop · close_to_tray

## 十、变更记录

- **v4.6**：界面适配改进——动态窗口尺寸（`_fit_window`，中英文宽度自适应）、
  坐标标签超长省略、回放预览自动换行、全局字体改微软雅黑、顶栏改悬浮圆角卡片、
  托盘"退出"与关闭到托盘行为区分（`_quit` 标志）；移除多点列表"＋添加当前"
  快捷按钮与若干未使用的文案键；清理重复导入与冗余主题色键。
- **v4.5**：功能冻结基线（本档所述架构与坑位均以此版为准）。
