---
name: pyinstaller-packaging
description: 将 Python 项目打包为 Windows 可分发的 .exe 可执行程序。当用户要求"打包""构建 exe""出包""PyInstaller""打一个 vX.X 版本"或涉及 build.py/dist 产物时使用。
---

# Python 打包 EXE——PyInstaller 实战

## 核心流程

```
源码 + 依赖 → PyInstaller 分析 → 资源收集 → 打包 → dist/ 产出 .exe
```

## 基础命令

### 单文件打包（推荐分发用）

```bash
pyinstaller --onefile \
  --name "MyApp" \
  --icon=assets/icon.ico \
  --add-data "assets;assets" \
  --add-data "config.json;." \
  main.py
```

### 目录打包（推荐调试用，启动快）

```bash
pyinstaller --onedir \
  --name "MyApp" \
  --icon=assets/icon.ico \
  --add-data "assets;assets" \
  main.py
```

### 关键参数速查

| 参数 | 作用 | 备注 |
|------|------|------|
| `--onefile` | 打包为单个 .exe | 启动慢（需解压），杀毒软件易误报 |
| `--onedir` | 打包为目录 | 启动快，调试优先选这个 |
| `--name` | 输出文件名 | 不含 .exe 后缀 |
| `--icon` | 程序图标 | 仅 .ico 格式有效 |
| `--add-data "源;目标"` | 嵌入数据文件 | **Windows 用分号**，Linux 用冒号 |
| `--hidden-import` | 显式声明隐式依赖 | 解决 `ModuleNotFoundError` |
| `--collect-all <包名>` | 收集包的全部文件 | 替代逐个 --hidden-import |
| `--noconsole` | 不显示控制台窗口 | GUI 程序用 |
| `--clean` | 构建前清理缓存 | 遇到诡异 bug 时先试这个 |

## 常见坑与解法

### 1. `ModuleNotFoundError`（隐式 import）

某些库用 `__import__()` / `importlib` 动态加载，PyInstaller 无法静态分析到。

**症状**：运行时 `No module named 'xxx'`

**解法**：
```bash
--hidden-import xxx
# 或批量收集：
--collect-all xxx_package
```

### 2. `--add-data` 路径分隔符

**Windows 用分号，Linux 用冒号**——混用会导致文件找不到。

```bash
# Windows（正确）
--add-data "templates;templates"
# Linux（正确）
--add-data "templates:templates"
```

### 3. 杀毒软件误报

`--onefile` 打包的 .exe 本质是自解压归档，壳特征容易被杀软识别。

**缓解方法**：
- 优先用 `--onedir` 分发（误报率大幅降低）
- 用 `--clean` 确保无旧签名残留
- 给 .exe 加数字签名（如 `signtool`）

### 4. 运行时找不到数据文件

PyInstaller 把数据文件解压到临时目录 `sys._MEIPASS`，代码里必须适配：

```python
import sys, os

def resource_path(relative_path):
    """获取资源绝对路径，兼容打包和开发模式。"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

# 使用
config = open(resource_path("config.json")).read()
```

### 5. 版本号嵌入

通过 `--version-file` 传入 Windows 版本信息文件（`file_version_info.txt`），让 .exe 右键属性显示版本号。详见 `references/version-info.md`。

### 6. 打包后体积过大

| 原因 | 解法 |
|------|------|
| 虚包把所有子模块都拖进来了 | 指定具体子模块：`--hidden-import pkg.sub` 替代 `--collect-all pkg` |
| numpy/pandas/torch 等重型库 | 换轻量替代或按需 import |
| 包含了测试/文档 | 用 `.spec` 文件 exclude |
| UPX 压缩未启用 | `--upx-dir` 指定 UPX 路径 |

## .spec 文件（进阶控制）

当命令行参数不够用时，用 .spec 文件精细控制：

```bash
# 生成 .spec 模板
pyi-makespec --onefile --name MyApp main.py
# 编辑 MyApp.spec 后构建
pyinstaller MyApp.spec
```

.spec 常见定制点见 `references/spec-examples.md`。

## 典型工作流

### 发布版本打包

```bash
# 1. 清理旧产物
rm -rf build/ dist/ *.spec
# 2. 构建
pyinstaller --onefile --clean --name "MyApp_v1.0" --icon=icon.ico main.py
# 3. 验证
dist/MyApp_v1.0.exe --version
# 4. 分发（压缩或安装包）
```

### 调试打包问题

```bash
# 先 --onedir 验证功能
pyinstaller --onedir --clean main.py
# 确认能跑通再 --onefile
pyinstaller --onefile --clean main.py
```

## Q&A 机制与项目配置

为避免每次打包重复询问相同的项目信息，使用 `packaging.json` 持久化静态配置。详见 `references/qa-flow.md`。

### 配置策略

| 存储类型 | 内容 | 举例 |
|---------|------|------|
| **存 JSON（复用）** | 软件名、公司主体、入口文件、图标、打包模式、数据文件、隐式 import | `"name": "MyApp"` |
| **每次询问** | 版本号、本次特殊需求、是否临时切换模式 | `"version": "2.1.0"` |

### 流程概要

1. 检查项目根目录是否有 `packaging.json`
2. 有 → 加载并确认各字段是否仍正确，过时的更新
3. 无 → 逐项询问后生成 `packaging.json`
4. 始终询问版本号（每次发版会变）
5. 从 JSON 拼装 `pyinstaller` 命令，执行构建

JSON 模板见 `references/project-config-template.json`。

## 触发场景

- "打包"、"出包"、"构建 exe"、"打一个 vX.X 版本"
- "PyInstaller"、"pyinstaller"
- 涉及 build.py / build.sh 打包脚本
- 分发 Python 程序给非开发者

## 执行步骤

1. **加载/生成配置**：读取或新建 `packaging.json`（按 Q&A 流程逐项确认）
2. **确认版本号**：每次必问，填入 JSON
3. **确认依赖**：检查 `requirements.txt`，标记隐式 import 库
4. **确认数据文件**：校验 `--add-data` 清单，代码里 `resource_path()` 适配就位
5. **选择模式**：调试用 `--onedir`，分发用 `--onefile`（可临时覆盖 JSON 默认值）
6. **构建**：从 JSON 拼装参数，执行 `pyinstaller`
7. **验证**：在干净环境（或 dist/ 目录）运行 .exe，确认所有功能正常
8. **保存配置**：将本次确认的变更写回 `packaging.json`
9. **打包分发**：zip 压缩 dist/ 目录，命名含版本号
