# Q&A 流程详述

执行打包任务时按以下流程与用户交互，兼顾复用与灵活性。

## 第一步：加载现有配置

检查项目根目录是否已有 `packaging.json`：

```
→ 存在 → 加载并展示摘要，逐项确认是否仍正确
→ 不存在 → 进入新建流程
```

### 加载后展示示例

```
已加载 packaging.json：
  软件名：MyApp
  入口文件：main.py
  公司主体：xxx 公司
  打包模式：单文件 (--onefile)
  图标：assets/icon.ico
  显示控制台：是
  数据文件：assets → assets, config.json → .
  隐式 import：无
  排除模块：tkinter, unittest, email, html
  UPX 压缩：否

这些信息是否需要更新？[是/否]
```

## 第二步：新建 / 更新配置

### 必须确认（每次打包）

| 问题 | JSON 字段 | 说明 |
|------|----------|------|
| 版本号 | `app.version` | 每次发版必变，不存历史值 |
| 本次是否有临时变更 | — | 如临时新增依赖、额外数据文件、临时切 --onedir 调试 |

### 新建时询问（存 JSON 复用）

按顺序逐项确认，用户可直接回车接受默认值（括号内）：

1. 软件名 `[从入口文件名推断]`
2. 入口文件 `[main.py]`
3. 公司名称
4. 打包模式 `[onefile]` — onefile / onedir
5. 图标路径 `[assets/icon.ico]` — 无则跳过
6. 是否显示控制台窗口 `[true]` — GUI 程序选 false
7. 数据文件清单 — 逐项添加，空行结束
8. 隐式 import 清单 — 逐项添加，空行结束
9. 排除模块 — 默认建议 `["tkinter", "unittest", "email", "html"]`
10. 是否启用 UPX 压缩 `[false]`

## 第三步：拼装命令

从 JSON 提取参数，拼装 `pyinstaller` 命令行：

```python
import json

with open("packaging.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

cmd = ["pyinstaller"]

# 模式
mode = cfg["packaging"]["mode"]
cmd.append(f"--{mode}")

# 名称 + 版本号
name_ver = f"{cfg['app']['name']}_v{cfg['app']['version']}"
cmd += ["--name", name_ver]

# 清理
cmd.append("--clean")

# 图标
icon = cfg["packaging"].get("icon")
if icon:
    cmd += ["--icon", icon]

# 控制台
if not cfg["packaging"].get("console", True):
    cmd.append("--noconsole")

# 数据文件
for dd in cfg["resources"].get("data_dirs", []):
    cmd += ["--add-data", f"{dd['src']};{dd['dest']}"]

# 隐式 import
for hi in cfg["resources"].get("hidden_imports", []):
    cmd += ["--hidden-import", hi]

# 排除
for ex in cfg["resources"].get("excludes", []):
    cmd += ["--exclude-module", ex]

# 入口
cmd.append(cfg["app"]["entry"])

# 执行
print(" ".join(cmd))
```

## 第四步：保存配置

构建成功后，将本次确认的信息写回 `packaging.json`（版本号保留本次值作为下次的参考，但下次仍然会重新询问）。

## 交互示例

```
用户：帮我打包

AI：检测到 packaging.json，加载中...

已加载配置：
  软件名：MoneyFlyToMe
  入口：app.py
  版本号：(待确认)
  模式：单文件
  ...

请确认版本号：[1.2.0]
> 1.3.0

是否有本次临时变更？[无]
> 无

配置确认完毕，执行构建：
  pyinstaller --onefile --clean --name MoneyFlyToMe_v1.3.0 ...

构建完成 ✓
  → dist/MoneyFlyToMe_v1.3.0.exe (45MB)
  → packaging.json 已更新版本号为 1.3.0
```
