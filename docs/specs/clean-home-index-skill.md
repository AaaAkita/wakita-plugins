# clean-home：大模块结构审查编排 skill

**日期**: 2026-11-20
**状态**: 开发完成
**完成日期**: 2026-11-20

## 摘要

把原来单文件形式的 `ai-fullstack-review` 拆成「1 个编排 skill + 领域 skill 各归其位」：新增 `clean-home` 只负责审查步骤、路由和报告契约；把安全、契约、测试、复用等判据回填到已有 skill；把 AI 特有失败、结构量化、spec 对齐拆成 3 个新 skill。同时在 UserPromptSubmit hook 注入第 9 条规范和触发词提示，解决「重要 skill 不会被主动调用」的问题。

同日补充：把 10 个高频 skill 的触发词从 description 末尾迁到 `when_to_use`，description 压到 250 字符以内，清零「触发词落在触发窗口外」的风险。

## 背景与目标

- 原 `ai-fullstack-review.md` 是一个横向全栈审查，内容与 `robust-architecture`、`project-compliance-check`、`code-reuse-audit`、`test-quality-principles` 等大量重叠。
- 直接把原文件做成第 35 个 skill 会违反仓库「重叠优先扩写，不新建平行 skill」的约定，也会让审查规则出现多套真源。
- 目标：保留原 skill 的横向体检价值，同时让领域规则回各自的家；用索引 skill + hook 解决触发问题。

## 方案

### 新增 skill（4 个）

| Skill | 定位 | 内容来源 |
|-------|------|----------|
| `clean-home` | 编排入口：只写步骤、路由、级别合成、证据规则、报告骨架 | 原 §3/§4/§6/§7 + 新增「房间」隐喻 |
| `spec-alignment-review` | 实现与 spec/需求对齐审查 | 原 A 组（A1-A4） |
| `ai-code-failure-modes` | AI 生成代码特有失败模式 | 原 D2 + 补充检测方法 |
| `code-structure-metrics` | 结构混乱信号量化 | 原 E1/E3/E5/E7 + 默认阈值 |

### 回填现有 skill

| 现有 skill | 回填内容 |
|------------|----------|
| `robust-architecture` | B1-B3 契约、E4 未分层、D3 可回滚、E1 配置硬编码 |
| `project-compliance-check` | AI 生成代码安全补充（依赖可信、敏感模块人审、常规漏洞），不计入 28 项评分 |
| `test-quality-principles` | D1 测试存在性、证据缺失、AI 特有假象 |
| `code-reuse-audit` | E2/E6 审查信号与级别 |
| `idempotent-migration` | 迁移/配置回滚审查 |
| `vue2-elementui-standards` | 视觉硬编码与单一来源违反 |

### Hook 改造

- `wakita-userpromptsubmit.py` 的 `_NORMS` 增加第 9 条：大模块写完后先加载 `clean-home`。
- 新增 `_REVIEW_KEYWORDS` / `_REVIEW_HINT`，命中「模块写完了」「帮我审」「结构太乱」「该不该重构」「清理房间」「clean-home」等触发词时加强提示。
- `_detect_context` 改为可同时返回打包提示和审查提示，互不覆盖。

## 技术要点 ★

### 涉及文件

- `plugins/wakita-toolkit/skills/clean-home/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/spec-alignment-review/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/ai-code-failure-modes/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/code-structure-metrics/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/robust-architecture/SKILL.md` — 追加审查判据
- `plugins/wakita-toolkit/skills/project-compliance-check/SKILL.md` — 追加 AI 安全补充
- `plugins/wakita-toolkit/skills/test-quality-principles/SKILL.md` — 追加审查判据
- `plugins/wakita-toolkit/skills/code-reuse-audit/SKILL.md` — 追加审查信号
- `plugins/wakita-toolkit/skills/idempotent-migration/SKILL.md` — 追加回滚审查
- `plugins/wakita-toolkit/skills/vue2-elementui-standards/SKILL.md` — 追加审查判据
- `plugins/wakita-governance/hooks/wakita-userpromptsubmit.py` — 第 9 条规范 + 触发词提示
- 版本与文档：两个 `plugin.json`、两个 `kimi.plugin.json`、`marketplace.json`、`AGENTS.md`、`README.md`

### 关键约束

- `clean-home` 不复制领域规则，只写「这一步做什么 + 加载哪个 skill」。
- 每个新 skill 的 `name` 必须等于目录名；`description` 不超过 1024 字符，触发词放在前 250 字符内。
- 审查默认只出报告，不改代码；修复一次只处理一个优先级批次。
- skill 加载失败记「证据缺失」，不得当通过。
- hook 始终 exit 0；非对象/空输入降级放行。

### 路由表

| 步骤 | 目的 | 加载 |
|------|------|------|
| 0 | 界定范围/模式/spec | 无 |
| 1 | 对齐 spec | `spec-alignment-review` |
| 2 | 契约一致 | `robust-architecture` |
| 3 | 安全 | `project-compliance-check` |
| 4 | 验证/AI 假完成 | `test-quality-principles` + `ai-code-failure-modes` |
| 5 | 结构 | `code-structure-metrics` + `code-reuse-audit`；E4 回 `robust-architecture` |
| 6 | 数据/部署（按需） | `idempotent-migration` / `cd-deploy-verification` / `docker-compose-prod-default` |
| 7 | 汇总 | `clean-home` 报告契约 |

## 描述触发窗口归一化（同日补充）

ZCode 触发时只把 description 截断到约 250 字符给模型看，末尾的「触发词：…」可能看不到。同日把 10 个高频 skill 的触发词迁到独立的 `when_to_use` 字段，description 只保留「是什么 + 什么时候用」：

| Skill | description 原 → 现 | when_to_use |
|---|---:|---:|
| `playwright-cookie-injection-pitfalls` | 573 → 143 | 205 |
| `param-refactor-semantic-audit` | 361 → 79 | 93 |
| `docker-compose-prod-default` | 485 → 119 | 167 |
| `idempotent-migration` | 334 → 57 | 124 |
| `test-quality-principles` | 312 → 87 | 160 |
| `robust-architecture` | 274 → 53 | 152 |
| `cd-deploy-verification` | 272 → 63 | 116 |
| `mysql-expert` | 260 → 72 | 139 |
| `vue2-elementui-standards` | 295 → 74 | 158 |
| `code-reuse-audit` | 146 → 84 | 60（仅补 `when_to_use`） |

剩余 8 个 description 仍 >250，但「触发词：」标记都在前 250 字符内（只有末尾几个字被截），暂不处理：`compose-cd-deploy-pitfalls`、`canvas-interaction-space`、`plugin-creator`、`chinese-commit-messages`、`taxonomy-normalization`、`config-sync-guard`、`maxscript-pitfalls`、`schema-migration-convergence`。

验证结果：39 个 skill 中 `description > 1024` 为 0，`触发词标记 > 250` 为 0；`when_to_use` 共 14 个（4 个新 skill + 10 个现有 skill）。

## 影响范围

- toolkit 34 → 38 个 skill（新增 4 个）；总 skill 数 35 → 39。
- toolkit 版本 1.8.0 → 1.9.0；governance 版本 2.7.0 → 2.8.0。
- UserPromptSubmit 注入内容从 8 条规范变为 9 条，并新增结构审查触发词提示。
- 原有 skill 只追加审查判据，不改变既有正文和触发词。

## 待确认

- [x] 4 个新 skill frontmatter 的 `name` 与目录名一致
- [x] 所有 `description` 均 < 1024 字符，触发词在前 250 字符内
- [x] `clean-home` 引用的 10 个 skill 均存在
- [x] hook `py_compile` 通过；8 组输入均 exit 0 且输出合法 JSON
- [x] 打包提示与审查提示可同时命中，互不覆盖
- [x] 版本号、skill 计数在 plugin.json / kimi.plugin.json / marketplace.json / AGENTS.md / README.md 一致
- [x] 原有 skill 的审查判据以交叉引用为主，未复制大段规则
- [x] 10 个高频 skill 的 description ≤250，触发词迁到 `when_to_use`
- [x] 39 个 skill 中不再有「触发词标记超过 250」的情况
- [x] `when_to_use` 共 14 个（4 新 + 10 现有）
- [x] 剩余 8 个 >250 的 description，触发词均在前 250 字符内，暂不处理

## 未做

- 未新增子智能体，也未修改 `using-wakita` 的 agent 调度流程。审查仍由主智能体加载 `clean-home` 后执行；如需隔离/并行，后续再给 `wakita-auditor` 加「结构体检模式」。
- 未新增 command。若后续需要引擎级强制加载，可评估用 command 的 `skills:` 自动挂载，但那会改变 toolkit「纯 skill 插件」的定位。
- 其余 8 个 description >250 的 skill 未改；触发词在前 250 字符内，等下次修改该 skill 时顺手归一化。
