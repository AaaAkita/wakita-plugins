#!/usr/bin/env python3
"""UserPromptSubmit hook —— 工作规范软提醒 + 场景提示。

每次用户提交 prompt 时注入轻量规范提示。不强制任何行为，仅作为上下文参考。

协议：stdin 读 JSON，stdout 输出 JSON，必须 exit 0。
"""

import json
import sys

# Codex/ZCode 均按 UTF-8 解析 hook 的 stdin/stdout；Windows 下 Python 默认使用
# 本地代码页（如 GBK），需显式统一为 UTF-8，否则中文输出会乱码。
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass

# 工作规范（始终注入，软提醒）
_NORMS = """\
[wakita 工作规范]
1. 提交信息（commit message）使用中文，类型前缀用英文。
2. 改动代码前先定位，结论带「文件:行号」证据。
3. 找不到证据明说"未找到"，不臆测。
4. 危险操作（rm -rf / 强推 / DROP 等）会被自动拦截。
5. 分支合并至主干后可复盘：有无可复用方案值得沉淀为 skill。
6. 接到代码改动需求时，按 using-wakita 工作流执行：先查 docs/specs/ 有无现成 spec → 分级（小/中/大）→ 中/大任务写 spec 留档 → Plan 用 EnterPlanMode 制定 → 调度 scout/builder/auditor（深水区 Bug 升级 wakita-ace 攻坚）→ auditor 通过后标记 spec「开发完成」。
7. 需求模糊时先加载 brainstorm skill 做头脑风暴，想清楚再写 spec。禁止直接开写。
8. 调用子智能体时，同一任务/阶段/角色优先用 SendMessage + 原 agentId 延续已有子会话，不要无理由新开（重开会丢失缓存，贵模型成本尤其高）；换阶段/换角色/会话失效才新开。
9. 大模块写完后、准备继续叠加功能前，先加载 clean-home skill 做结构审查（清房间）；它只做编排，会按步骤加载领域 skill。审查默认只出报告，不改代码。"""

# 打包关键词 → 场景提示
_PACK_KEYWORDS = [
    "打包", "出包", "构建 exe", "build.py", "build.sh",
    "pyinstaller", "PyInstaller", "打一个 v", "发布版本",
    "打包成exe", "打包为exe",
]

_PACK_HINT = """\
[pyinstaller-packaging]
- packaging.json 存在 → 只确认版本号 + 临时变更
- 不存在 → 5 个默认值问题（回车跳过）
- 构建成功后自动写回 JSON"""

# 结构审查关键词 → 编排入口提示（clean-home 只做编排，规则在领域 skill）
_REVIEW_KEYWORDS = [
    "模块写完了", "模块写完", "帮我审", "结构太乱", "代码太乱",
    "结构不对", "代码看不懂", "该不该重构", "能不能继续加",
    "清理房间", "clean-home",
]

_REVIEW_HINT = """\
[clean-home 清理房间]
- 命中结构审查触发词：先加载 clean-home skill，按它的步骤逐项加载领域 skill。
- clean-home 只做编排，不替代领域 skill；默认只出报告，不改代码。"""


def _as_text(value):
    """只接受字符串；prompt/text 字段若为列表或 None 返回空串，避免 .lower() 崩溃。"""
    return value if isinstance(value, str) else ""


def _detect_context(prompt_text):
    if not prompt_text:
        return ""
    lowered = prompt_text.lower()
    hints = []
    if any(kw.lower() in lowered for kw in _PACK_KEYWORDS):
        hints.append(_PACK_HINT)
    if any(kw.lower() in lowered for kw in _REVIEW_KEYWORDS):
        hints.append(_REVIEW_HINT)
    return "\n\n".join(hints)


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError):
        sys.exit(0)

    # stdin 可能是 list/str/null（非对象），直接 return 而不是抛 AttributeError
    if not isinstance(input_data, dict):
        sys.exit(0)

    prompt = _as_text(input_data.get("prompt")) or _as_text(input_data.get("text"))

    parts = [_NORMS]
    extra = _detect_context(prompt)
    if extra:
        parts.append(extra)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n\n".join(parts),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — hook 异常不得阻塞用户输入
        print(json.dumps({
            "systemMessage": f"[wakita] UserPromptSubmit hook 异常，已降级放行：{exc}"
        }, ensure_ascii=False))
        sys.exit(0)
