"""规则配置中心 —— 危险命令黑名单、保护文件清单。

被 pretooluse.py / posttooluse.py / commands/lock.md 共同引用。
保护清单存在 WAKITA_PROTECT_FILE（默认 rules.protected.json），
lock 命令可往里追加文件，pretooluse 实时读取。
"""

import json
import os
import re

# 保护清单文件路径（与本文件同目录）
_PROTECT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.protected.json")

# 默认保护文件（lock 命令追加的会合并进来）
DEFAULT_PROTECTED_FILES = [
    ".env",
    ".env.local",
    ".env.production",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".git/config",
    ".git/HEAD",
    ".gitignore",
]

# 危险命令黑名单：每条 = (正则, 阻断原因)
# 正则对命令字符串做 re.search（大小写不敏感）
DANGEROUS_COMMANDS = [
    # —— 递归删除根/家目录 ——
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+/(?:\s|$)", "禁止递归删除根目录 /"),
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+~(?:\s|$)", "禁止递归删除家目录 ~"),
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+/\*", "禁止递归删除根目录下所有文件 /*"),
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+[A-Z]:\\(?:\s|$)", "禁止递归删除盘符根目录（如 C:\\）"),
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+%USERPROFILE%", "禁止递归删除用户目录"),
    # —— 强制推送主分支 ——
    (r"\bgit\s+push\s+(?:--force|--force-with-lease|-f)\b.*\b(?:main|master)\b",
     "禁止强制推送到 main/master 分支"),
    (r"\bgit\s+push\s+-f\s+origin\s+(?:main|master)\b",
     "禁止强制推送到 main/master 分支"),
    # —— 硬重置无目标 ——
    (r"\bgit\s+reset\s+--hard\s*(?:$|&&|\||;)",
     "git reset --hard 必须指定 commit，禁止裸重置"),
    # —— 危险 SQL ——
    (r"\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b", "禁止 DROP TABLE/DATABASE/SCHEMA"),
    (r"\bTRUNCATE\s+TABLE\b", "禁止 TRUNCATE TABLE"),
    # —— 权限/系统 ——
    (r"\bchmod\s+-R\s+777\s+/(?:\s|$)", "禁止对根目录递归 777"),
    (r"\bmkfs\b", "禁止格式化文件系统（mkfs）"),
    (r"\bdd\s+if=.*of=/dev/", "禁止 dd 写入设备文件"),
    (r":\(\)\{\s*:\|:\s*&\s*\};\s*:", "禁止 fork bomb"),
]

# 保护文件命中时的提示
PROTECTED_FILE_MSG = "该文件受 wakita-governance 保护，禁止修改/删除：{path}"


def load_protected_files():
    """读取保护清单（默认 + 用户追加的合并）。"""
    files = list(DEFAULT_PROTECTED_FILES)
    if os.path.exists(_PROTECT_FILE):
        try:
            with open(_PROTECT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                extra = data.get("protected_files", [])
                for p in extra:
                    if p not in files:
                        files.append(p)
        except (json.JSONDecodeError, OSError):
            pass  # 读取失败则只用默认清单，不阻断工作
    return files


def add_protected_file(path):
    """lock 命令调用：追加一个保护文件。返回是否新增。"""
    files = load_protected_files()
    # 标准化路径
    norm = path.replace("\\", "/").lstrip("./")
    if norm in files:
        return False
    files.append(norm)
    data = {"protected_files": [f for f in files if f not in DEFAULT_PROTECTED_FILES]}
    with open(_PROTECT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def match_dangerous_command(command):
    """检查命令是否命中黑名单。返回 (reason, None) 或 (None, None)。"""
    for pattern, reason in DANGEROUS_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return reason
    return None


def is_path_protected(file_path):
    """检查文件路径是否在保护清单内（末尾匹配）。"""
    norm = file_path.replace("\\", "/")
    for protected in load_protected_files():
        if norm.endswith(protected) or norm == protected:
            return protected
    return None
