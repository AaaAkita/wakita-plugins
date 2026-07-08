---
name: automatic-script-tool-build
description: 打包 AutomaticScriptTool (E:\software\AutomaticScriptTool) 为可分发的 Windows 可执行程序。当用户要求"打包""构建""出包""打一个 vX.X 版本"或涉及 build.py / dist 产物时使用。涵盖 PyInstaller 构建、版本号命名、Chromium 浏览器拷贝、zip 压缩、产物验证全流程。
---

# AutomaticScriptTool 打包构建

打包 AutomaticScriptTool（Visual Playwright 脚本自动化工具）为免安装 Windows 可执行程序。

## 项目位置

`E:\software\AutomaticScriptTool`

## 何时使用

- 用户说"打包""构建""出包""打 vX.X 版本"
- 涉及 build.py、dist 目录、PyInstaller 构建
- 用户拿到项目源码要生成分发包

## 前置检查

构建前必须确认环境就绪，否则 PyInstaller 会失败或产物缺浏览器：

```bash
cd E:/software/AutomaticScriptTool
python -c "import PyInstaller; print('PyInstaller', PyInstaller.__version__)"
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); exe=p.chromium.executable_path; p.stop(); import os; print('chromium:', exe, os.path.exists(exe))"
ls launcher.py
```

三项都通过才能构建。缺 PyInstaller 用 `pip install pyinstaller`；缺 Chromium 用 `python -m playwright install chromium`。

## 构建流程

### 1. 运行 build.py

build.py 内部三步：清理旧 dist/build -> PyInstaller 打包 -> 拷贝 Playwright Chromium。

```bash
cd E:/software/AutomaticScriptTool && python build.py 2>&1 | tail -15
```

耗时约 3-5 分钟。成功的标志是末尾输出 `Build complete. Output in dist/AutomaticScriptTool`。

**`tbb12.dll` 警告可忽略**——是 numba 的可选依赖，不影响运行。

### 2. 验证产物

构建后必须核对产物完整，不能直接打包发出去：

```bash
cd E:/software/AutomaticScriptTool/dist
ls -la AutomaticScriptTool/AutomaticScriptTool.exe          # 入口，约 24MB
ls AutomaticScriptTool/browsers/                            # chromium-XXXX + ffmpeg-XXXX
ls -d AutomaticScriptTool/_internal/static AutomaticScriptTool/_internal/core AutomaticScriptTool/_internal/flows
```

三个数据目录（static/core/flows）必须存在，否则前端/引擎/方案缺失。

### 3. 加版本号 + 打 zip

build.py 输出到固定的 `dist/AutomaticScriptTool`，没有版本号。按用户指定的版本号重命名并压缩：

```bash
cd E:/software/AutomaticScriptTool/dist
# 先清理旧版本目录/zip，避免混淆
rm -rf AutomaticScriptTool-vX.Y AutomaticScriptTool-vX.Y.zip 2>/dev/null
# 重命名
mv AutomaticScriptTool AutomaticScriptTool-vX.Y
# 打 zip（PowerShell 的 Compress-Archive，Windows 原生）
powershell -Command "Compress-Archive -Path 'AutomaticScriptTool-vX.Y' -DestinationPath 'AutomaticScriptTool-vX.Y.zip' -Force"
ls -lh AutomaticScriptTool-vX.Y.zip    # 约 300MB
```

**版本号约定**：用户说"打包一个 v2.3 版本" -> 目录名 `AutomaticScriptTool-v2.3`，zip 名 `AutomaticScriptTool-v2.3.zip`。

## 产物结构

```
dist/AutomaticScriptTool-vX.Y/
├── AutomaticScriptTool.exe   # 入口（双击运行，windowed 模式无控制台）
├── _internal/                # PyInstaller onedir 模式的依赖
│   ├── core/                 # 引擎、步骤、工具
│   ├── static/              # 前端（index.html + js + css）
│   ├── flows/               # 方案目录（gitignore，但打包时包含本地方案）
│   ├── pandas/、playwright/、flask/ 等依赖
│   └── base_library.zip
└── browsers/                 # build.py 第3步拷入
    ├── chromium-1124/         # 当前 Playwright 对应的 Chromium 版本目录
    └── ffmpeg-1009/          # 编解码辅助
```

## build.py 关键机制

- **`--onedir`**：onedir 模式，生成 exe + _internal 目录（非单文件）。启动快，便于排错。
- **`--windowed`**：GUI 模式，无控制台窗口。
- **`--add-data`**：static、core、flows 三个目录随包打入。
- **`--exclude-module`**：排除 PyQt/torch/scipy/matplotlib 等无关大模块，减小体积。
- **`get_required_chromium_revision()`**：动态探测当前 playwright 所需 Chromium 版本目录（如 chromium-1124），精确拷贝，避免多版本共存时拷错。
- **flows 目录**：被 .gitignore 忽略，但打包时会包含本地已存在的方案文件。

## build/ 与 dist/ 的区别

两者都是 PyInstaller 一次构建产生，**不是两种构建方式**：

- **`build/`**：中间工作区。`.toc`/`.pyz`/`.pkg` 等清单和半成品，构建后无用，可安全删除。build.py 每次用 `--clean` 重建。
- **`dist/`**：最终可分发产物。exe + 依赖 + 浏览器，自包含可运行。

用户分发的只有 dist 里带版本号的 zip。

## 常见问题

**构建失败 / 找不到模块**：检查 hidden_imports（build.py 里列了 pandas、playwright.sync_api、flask、eventless、engineio）。新增依赖后要补进 hidden_imports，否则打包后运行时报 ImportError。

**产物缺浏览器 / 启动后报浏览器找不到**：build.py 第3步拷贝 Chromium 失败。检查 `C:\Users\Administrator\AppData\Local\ms-playwright` 下是否有对应版本目录。

**体积过大**：检查是否误打入 torch/scipy 等。确认 build.py 的 `--exclude-module` 列表完整。

**打包后前端白屏**：确认 `_internal/static/` 存在且含 index.html。`--add-data 'static;static'` 路径写错会导致前端缺失。

## 不要做的事

- 不要在 build.py 运行时去操作 dist 目录（会被 `--clean` 删除）。
- 不要把 build/ 目录也压缩进 zip，那是中间产物。
- 不要跳过验证步骤直接发 zip——曾经出现缺数据目录的情况。
- 构建前如未提交代码，先提示用户是否需要提交（用户可能想打包最新代码）。
