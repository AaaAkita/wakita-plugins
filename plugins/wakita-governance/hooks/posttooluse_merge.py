#!/usr/bin/env python3
"""PostToolUse hook —— 分支合并复盘：主动探索 + 展示候选。

检测 git merge 到 main/master 后：
1. 收集本次合并的改动范围（git diff --stat / git log）
2. 注入 systemMessage，命令 AI 立即执行复盘分析
3. AI 主动向用户展示可泛化为 skill 的候选内容，而非被动提问

协议：stdin 读 JSON，stdout 输出 JSON，必须 exit 0。
"""

import json
import os
import re
import subprocess
import sys

_CHECKOUT_AND_MERGE = re.compile(
    r"\bgit\s+checkout\s+(?:main|master)\b.*\bgit\s+merge\b",
    re.IGNORECASE,
)
_MERGE_NOT_MAIN = re.compile(
    r"\bgit\s+merge\s+(?!origin/?(?:main|master)\b|main\b|master\b)\S+",
    re.IGNORECASE,
)


def _get_merge_info():
    """收集本次合并的改动摘要。"""
    info = {"files": "", "commits": ""}
    try:
        # 本次合并引入的改动文件
        files = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1..HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        info["files"] = files.stdout.strip()[-500:]  # 截断，避免超长
    except Exception:
        pass
    try:
        # 本次合并引入的提交
        commits = subprocess.run(
            ["git", "log", "--oneline", "HEAD~1..HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        info["commits"] = commits.stdout.strip()[-300:]
    except Exception:
        pass
    return info


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if input_data.get("tool_name") != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    if not (_CHECKOUT_AND_MERGE.search(command) or _MERGE_NOT_MAIN.search(command)):
        sys.exit(0)

    info = _get_merge_info()

    # 构造主动探索指令——不给 AI 偷懒反问的退路
    msg_parts = [
        "## 分支合并至主干，执行复盘",
        "",
        "请按以下步骤主动分析并直接展示结果，不反问、直接做：",
        "",
        "1. 定位改动范围（如已提供则直接使用）：",
    ]
    if info["files"]:
        msg_parts.append(f"   ```\n{info['files']}\n   ```")
    if info["commits"]:
        msg_parts.append(f"   提交列表：\n   ```\n{info['commits']}\n   ```")

    msg_parts += [
        "2. **派 wakita-scout 扫描改动文件**，识别以下三类可泛化内容：",
        "   - 重复模式：同一逻辑在多处出现（对照 code-reuse-audit 判断）",
        "   - 可复用组件/工具函数：独立、通用、有明确输入输出",
        "   - 排错经验：本次踩坑的根因+修复方案，值得固化",
        "3. **向用户展示候选清单**，格式：",
        "   | 内容 | 类型 | 建议 skill |",
        "   |------|------|-----------|",
        "   | xxx 工具函数被 3 处重复定义 | 工具函数 | xxx-utils |",
        "4. **逐条询问**：要将 xxx 沉淀为 skill 吗？而非开放式的有没有值得生成的",
        "5. 用户确认后，用 skill-creator 生成对应 skill，写入 $ZCODE_HOME/skills/",
    ]

    print(json.dumps({"systemMessage": "\n".join(msg_parts)}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
