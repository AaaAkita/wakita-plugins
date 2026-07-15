# Q&A 流程

## 决策树

```
用户说"打包"
  │
  ├─ packaging.json 存在？──是──→ 展示一行摘要 → 只问：版本号？有临时变更吗？
  │                                    │                 ↓
  └─ 不存在 ──→ 新建：问 5 个必要问题（有默认值，回车跳过） ←──┘
                                                    │
                                              拼装命令 → 构建 → 保存 JSON
```

## 首次打包（新建 packaging.json）

只问 **5 个必要问题**，其余字段用默认值，用户回车即接受：

| # | 问题 | 默认值 | 备注 |
|---|------|--------|------|
| 1 | 软件名？ | 从入口文件名推断 | `app.py` → `"App"` |
| 2 | 入口文件？ | `"main.py"` | 如不存在则要求指定 |
| 3 | 版本号？ | — | 必填，无默认值 |
| 4 | 打包模式？ | `"onefile"` | onefile（单文件）/ onedir（目录） |
| 5 | 有数据文件要打包吗？ | 无 | 有则逐项添加 `源→目标`，空行结束 |

**高级字段不主动问**（图标、公司名、隐式 import、UPX 等），用户明确提到时再追加到 JSON。优先让简单场景的用户 3 秒钟跳过。

## 后续打包（packaging.json 已存在）

**只问 2 个问题**，其余字段静默沿用：

1. **版本号？** — 必问，每次发版会变
2. **有临时变更吗？** — 如临时切 onedir 调试、新增依赖、加了数据文件

展示**一行摘要**让用户有个概念，不逐字段确认：

```
→ packaging.json: MyApp_v1.2.0 | onefile | main.py | 数据: assets/
→ 版本号？[1.2.0 →  ]
→ 临时变更？[无]
```

## 轻量模式

以下条件**全部满足**时，按轻量模式处理——跳过数据文件/隐式 import 等高级问题：

- 无 `--add-data` 需求
- 无隐式 import
- 无图标文件
- 无 UPX

轻量模式下首次也只问 3 个问题（软件名 + 入口 + 版本号），其余全默认。

## 拼装命令

从 `packaging.json` 提取参数，拼装为 `pyinstaller` 命令行。

```python
import json, subprocess

with open("packaging.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

cmd = ["pyinstaller", f"--{cfg['packaging']['mode']}", "--clean"]

# 名称含版本号
cmd += ["--name", f"{cfg['app']['name']}_v{cfg['app']['version']}"]

# 图标（可选）
if cfg["packaging"].get("icon"):
    cmd += ["--icon", cfg["packaging"]["icon"]]

# 控制台（可选）
if not cfg["packaging"].get("console", True):
    cmd.append("--noconsole")

# 数据文件
for d in cfg["resources"].get("data_dirs", []):
    cmd += ["--add-data", f"{d['src']};{d['dest']}"]

# 隐式 import
for hi in cfg["resources"].get("hidden_imports", []):
    cmd += ["--hidden-import", hi]

# 排除模块
for ex in cfg["resources"].get("excludes", []):
    cmd += ["--exclude-module", ex]

cmd.append(cfg["app"]["entry"])
subprocess.run(cmd)
```

## 保存配置

构建成功后写回 `packaging.json`（保留用户追加的高级字段，只更新版本号）。构建失败不写回。
