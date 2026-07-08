---
name: skill-installer
description: 从精选列表或 GitHub 仓库路径安装 Codex skill 到 $CODEX_HOME/skills。当用户要求列出可安装的 skill、安装精选 skill、或从其他仓库（包括私有仓库）安装 skill 时使用。
metadata:
  short-description: 从 openai/skills 或其他仓库安装精选 skill
---

# Skill 安装器

帮助安装 skill。默认来源是 https://github.com/openai/skills/tree/main/skills/.curated，用户也可以指定其他位置。实验性 skill 位于 https://github.com/openai/skills/tree/main/skills/.experimental，可用相同方式安装。

根据任务使用对应的辅助脚本：
- 用户询问有哪些可用的 skill，或使用本 skill 但未说明要做什么时，列出 skill。默认列出 `.curated`，询问实验性 skill 时传 `--path skills/.experimental`。
- 用户提供 skill 名称时，从精选列表安装。
- 用户提供 GitHub 仓库/路径（包括私有仓库）时，从该仓库安装。

用辅助脚本安装 skill。

## 沟通方式

列出 skill 时，根据用户请求的语境大致按以下格式输出。若询问的是实验性 skill，改从 `.experimental` 而非 `.curated` 列出，并相应标注来源：
"""
来自 {repo} 的 skill：
1. skill-1
2. skill-2（已安装）
3. ...
你要安装哪些？
"""

安装完 skill 后，告知用户："重启 Codex 以加载新 skill。"

## 脚本

以下脚本都需要联网，因此在沙箱中运行时应请求提权。

- `scripts/list-skills.py`（打印 skill 列表，并标注已安装项）
- `scripts/list-skills.py --format json`
- 示例（实验性列表）：`scripts/list-skills.py --path skills/.experimental`
- `scripts/install-skill-from-github.py --repo <owner>/<repo> --path <path/to/skill> [<path/to/skill> ...]`
- `scripts/install-skill-from-github.py --url https://github.com/<owner>/<repo>/tree/<ref>/<path>`
- 示例（实验性 skill）：`scripts/install-skill-from-github.py --repo openai/skills --path skills/.experimental/<skill-name>`

## 行为与选项

- 公共 GitHub 仓库默认走直接下载。
- 下载因鉴权/权限错误失败时，回退到 git sparse checkout。
- 目标 skill 目录已存在时中止安装。
- 安装到 `$CODEX_HOME/skills/<skill-name>`（默认 `~/.codex/skills`）。
- 多个 `--path` 值可在一次运行中安装多个 skill，每个以路径 basename 命名，除非显式传 `--name`。
- 选项：`--ref <ref>`（默认 `main`）、`--dest <path>`、`--method auto|download|git`。

## 注意事项

- 精选列表通过 GitHub API 从 `https://github.com/openai/skills/tree/main/skills/.curated` 获取。若不可用，解释错误并退出。
- 私有 GitHub 仓库可借助已有的 git 凭据访问，或通过可选的 `GITHUB_TOKEN`/`GH_TOKEN` 下载。
- git 回退先尝试 HTTPS，再尝试 SSH。
- 位于 https://github.com/openai/skills/tree/main/skills/.system 的 skill 已预装，无需帮用户安装。若用户询问，直接说明即可。若用户坚持，可下载覆盖。
- 已安装标注来自 `$CODEX_HOME/skills`。
