# wakita-governance agent model 注入脚本

wakita-governance 的三个子智能体（scout / auditor / builder）在 agent 文件 frontmatter 里硬编码了 `model:` 字段。ZCode 当前不在 agent `model:` 字段中展开环境变量或动态值，因此用户安装插件后若想切换到自己的 provider/model，需要通过本脚本注入。

## 脚本作用

把插件安装目录下 `agents/wakita-{scout,builder,auditor}.md` 三个文件 frontmatter 的 `model:` 字段写入 `custom:<provider>:<model-id>` 真实值。

- 自动探测最新已安装版本目录（1.10.0 > 1.9.0，用版本元组排序）
- 写前备份为 `.bak`
- 幂等：已是目标值则跳过，重复运行不出错
- 校验 provider/model 在 `~/.zcode/v2/config.json` 中真实存在，不存在则列出可选项并退出
- 同时支持 `provider` 为 dict（当前 ZCode）和 list（旧版兜底）两种结构
- 保留原文件 UTF-8 无 BOM 编码和换行风格（LF/CRLF）

## 用法

```bash
# 列出所有可用 provider 和 model
python scripts/inject-agent-model.py --list

# 默认 DeepSeek deepseek-v4-flash（与插件发布时的 frontmatter 一致，幂等无感）
python scripts/inject-agent-model.py

# 切换到其他 provider/model
python scripts/inject-agent-model.py --provider "builtin:bigmodel-coding-plan" --model GLM-5.2

# 指定版本（默认自动探测最新）
python scripts/inject-agent-model.py --version 2.0.4
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--provider` | `466f2f41-bacb-4168-b493-d0afa32a0357`（DeepSeek） | config.json 中 `provider.<key>` 的 `<key>` |
| `--model` | `deepseek-v4-flash` | 所选 provider 下 `models.<key>` 的 `<key>` |
| `--version` | 自动探测最新 x.y.z | 指定插件安装版本目录 |
| `--list` | - | 列出所有 provider+model 后退出 |

Provider key 中的 `:` 会被自动 URL 编码为 `%3A`（如 `builtin:bigmodel-coding-plan` -> `builtin%3Abigmodel-coding-plan`），最终写入值形如 `model: "custom:builtin%3Abigmodel-coding-plan:GLM-5.2"`。

## 路径说明

脚本操作的路径（自动定位，无需手动指定）：

| 平台 | 插件安装目录 | config.json |
|------|--------------|-------------|
| macOS / Linux | `~/.zcode/cli/plugins/cache/wakita-plugins/wakita-governance/<version>/` | `~/.zcode/v2/config.json` |
| Windows | `%USERPROFILE%\.zcode\cli\plugins\cache\wakita-plugins\wakita-governance\<version>\` | `%USERPROFILE%\.zcode\v2\config.json` |

## 回滚

每个文件写前都会生成 `.bak` 备份。如需回滚：

```bash
# macOS/Linux 示例
cp agents/wakita-scout.md.bak agents/wakita-scout.md

# Windows PowerShell 示例
Move-Item .\agents\wakita-scout.md.bak .\agents\wakita-scout.md -Force
```

## 跨平台说明

本脚本用 Python 实现，macOS / Linux / Windows 均可直接运行，无需维护多份等价脚本。相比 dev-plugin 的 `.sh` + `.ps1` 双脚本方案，本脚本额外处理了 `provider` 字段为 list 结构（旧版 ZCode）的情况，避免在 Windows 上因结构差异报"provider not found"。
