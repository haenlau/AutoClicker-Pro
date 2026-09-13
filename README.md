# AutoClicker Pro 🖱️

一个 Windows 桌面鼠标自动化工具：自动连点 + 宏录制回放，内置拟人化随机行为。

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 功能特性

- **自动连点**，三种坐标模式：
  - 跟随鼠标 —— 在当前鼠标位置连点
  - 固定坐标 —— 3 秒倒计时拾取屏幕位置
  - 多点循环 —— 坐标列表按顺序轮流点击
- **完整宏录制回放**：记录鼠标移动轨迹 + 按下/抬起事件，时间轴精确重放（支持拖动、双击）
- **点击动作**：单击 / 双击 / 拖动（多点循环下为 A→B→C 连拖）
- **拟人化**：高斯分布的点击间隔、5% 概率随机"走神"停顿、位置高斯偏移、随机按下时长
- **脚本库**：命名保存多个录制脚本，下拉即切换；配置导入/导出（含脚本）
- **系统托盘**：关闭即最小化到托盘，托盘菜单控制一切
- **全局热键**（任何窗口下有效）：`F6` 连点 · `F8` 录制 · `F9` 回放
- **紧急停止**：运行中把鼠标甩到屏幕左上角，所有动作立即停止
- 中英双语（跟随系统语言）· 浅色/深色主题 · 设置自动持久化

## 下载

前往 [Releases](https://github.com/haenlau/AutoClicker-Pro/releases) 下载免安装的单文件 exe（约 46MB）。

## 快速上手

1. 选择坐标模式（跟随鼠标 / 固定坐标 / 多点循环）
2. 设置点击间隔、按键与点击动作
3. `F6` 或点击"开始"启动连点；再按一次停止
4. 录制宏：`F8` 开始，操作鼠标，再按 `F8` 结束；`F9` 回放
5. **随时可以把鼠标甩到屏幕左上角紧急停止一切动作**

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
