"""审计日志写入器 —— 记录所有写操作与 git 提交。

日志写入 WAKITA_AUDIT_LOG 指定路径，默认 plugins/wakita-governance/audit.log
（被 .gitignore 排除，不入库）。append-only，每条一行 JSON。
"""

import json
import os
from datetime import datetime

# 日志文件：默认放在插件目录下，被 .gitignore 排除
_AUDIT_LOG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "audit.log",
)


def append_audit(tool_name, tool_input, summary=""):
    """追加一条审计记录。

    Args:
        tool_name: 工具名（Edit/Write/Bash 等）
        tool_input: 工具输入（dict）
        summary: 可选的额外说明
    """
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "tool": tool_name,
        "summary": summary,
    }
    # 提取关键信息，避免记录完整大块内容
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        # 命令太长只存前 200 字符
        entry["command"] = cmd[:200]
    elif tool_name in ("Edit", "Write", "MultiEdit"):
        entry["path"] = tool_input.get("file_path", "")
    elif tool_name == "Bash" and "git commit" in str(tool_input.get("command", "")):
        entry["op"] = "git-commit"

    try:
        with open(_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 日志写失败绝不影响主流程


def read_audit_lines(n=50):
    """读取最近 n 条审计记录（供 audit 命令调用）。"""
    if not os.path.exists(_AUDIT_LOG):
        return []
    try:
        with open(_AUDIT_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:]
    except OSError:
        return []
