---
name: ai-code-failure-modes
description: >
  AI 生成代码特有的失败模式审查——查 stub/假数据冒充核心逻辑、只覆盖快乐路径、调用不存在的 API 或依赖包、
  配置变更没验证、测试只断言当前实现、静默兜底掩盖失败。当用户说“AI 写的代码看着能跑但心里没底”
  “是不是 stub 冒充”“测试全过但功能没做”“AI 加了个不存在的包”“配置改了没生效”时使用。
  也作为 clean-home 清理房间的第 4 步被加载。只审 AI 特有失败模式，不重复测试规范与静默失败审计。
when_to_use: AI 主导开发的大模块验收；怀疑完成度是假的；测试通过但功能缺失；新增依赖/配置来源可疑；代码里出现 stub、TODO、假数据。
---

# AI 生成代码的失败模式

AI 写代码最常见的不是语法错，而是「看起来完成了」。本 skill 专门抓这些假完成信号。

## 失败模式清单

| ID | 模式 | 典型表现 | 级别建议 |
|---|---|---|---|
| D2-1 | stub 冒充核心逻辑 | `TODO`、`NotImplemented`、`pass`、`return {}`/`return None`、硬编码假数据、注释写「暂时这样」 | 核心逻辑 P0，边缘 P1 |
| D2-2 | 只覆盖快乐路径 | 没有空值/边界/异常分支；假设外部输入永远合法；失败时静默返回默认值 | 核心链路 P0/P1 |
| D2-3 | 幻觉 API/依赖 | import 了不存在的包、调用了不存在的方法/字段、照抄过时的库 API | P0 |
| D2-4 | 配置变更未验证 | 改了 env/compose/nginx/CI 但没有实际启动或验证；只改了样例文件 | P0/P1 |
| D2-5 | 测试镜像实现 | 测试断言的是当前实现而不是 spec 行为；Mock 了被测对象本身；只测快乐路径 | P1（测试规范细节见 `test-quality-principles`） |
| D2-6 | 静默兜底掩盖失败 | `except: pass`、`|| fallback`、失败也返回 success、通知/回写失败无人知晓 | P0/P1（详见 `silent-failure-audit`） |
| D2-7 | 大范围重写/无关改动 | 顺手重构、全文件格式化、无关重命名混进功能改动 | P1（范围对齐见 `spec-alignment-review`） |

## 检测方法

1. **搜 stub 和假数据**：
   ```bash
   grep -rnE "TODO|FIXME|NotImplemented|raise NotImplementedError|return \{\}|return None|pass  #|mock|fake|dummy" <范围>
   ```
   重点看这些位置是不是核心链路，而不是测试或占位模块。

2. **查依赖是否真实存在**：
   - 新增 import 逐个对照 `package.json` / `requirements.txt` / `pyproject.toml` / lockfile。
   - 对不认识的包，确认 registry 上存在、来源可信、版本已锁。
   - 对不认识的 API，查官方文档或类型定义，不要凭命名猜。

3. **查失败路径**：
   - 每个外部调用（HTTP/DB/文件/队列）是否有超时、异常分支、空结果处理。
   - 异常分支是返回错误，还是静默返回默认值/空列表。
   - 关键写操作失败时，调用方能不能感知。

4. **查配置变更**：
   - diff 里是否出现 env/compose/nginx/CI 变更。
   - 变更后有没有实际启动、健康检查、端到端验证；还是只改了文件就宣称完成。

5. **查测试是否真验证行为**：
   - 测试是否只断言「当前代码返回什么」，而不是 spec 要求的行为。
   - 是否 Mock 了被测对象本身；是否只覆盖快乐路径。
   - 更细的测试质量规则见 `test-quality-principles`。

## 输出

每条发现给：

- 模式 ID（D2-1 ~ D2-7）
- 证据：`文件:行` / 函数 / 调用链 / 命令输出
- 为什么这是假完成（一句话）
- 建议级别（P0/P1/P2，最终由 clean-home 汇总合成）
- 怎么补证据（如「跑一次真实请求」「查 registry」「补失败路径测试」）

## 边界

- 测试怎么写、断言是否合理 → `test-quality-principles`，本 skill 只标「测试可能没验证行为」。
- 静默失败链路、展示层指标失真 → `silent-failure-audit`，本 skill 只标「疑似静默兜底」。
- 实现是否偏离 spec → `spec-alignment-review`。
- 安全漏洞、依赖可信的合规判定 → `project-compliance-check`。
- 本 skill 不替代运行时验证；能跑测试/能启动服务的，优先用真实证据，不要只读代码下结论。
