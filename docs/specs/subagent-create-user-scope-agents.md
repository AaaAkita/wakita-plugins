# subagent-create 改为生成用户级子智能体

**日期**: 2026-08-12
**状态**: 开发完成
**完成日期**: 2026-08-12

## 摘要

三个子智能体（scout/auditor/builder）从「插件分发」改为「用户级生成」：插件不再携带 `agents/`，`/subagent-create` 命令执行时把三个 agent 的完整 md 文件写入 `~/.zcode/agents/`，frontmatter 同时支持 `model:` + `thoughtLevel:` + `injectAgentsMd:`。agent 正文模板保留在插件 `templates/agents/`（不在 ZCode 发现路径上，不注册为插件 agent），脚本复制模板并注入 frontmatter 值。已验证：ZCode 用户级 subagent 根目录为 `~/.zcode/agents/`，frontmatter 解析器原生支持 thoughtLevel/injectAgentsMd 字段。

## 背景与目标

- 问题：agent 随插件分发时，`model:` 硬编码在插件安装目录，切换模型要改插件缓存文件；且无法利用 ZCode 新支持的 `thoughtLevel`（思考强度）字段。
- 目标：agent 定义落到用户级目录，用户可自由编辑；`/subagent-create` 一站式完成「首次生成 + 切换模型/思考强度」。
- 成功标准：插件升级后 `wakita-governance:wakita-*` 三个插件级 agent 消失；`/subagent-create` 运行后 `~/.zcode/agents/` 出现三个可用 agent，新会话可调遣。

## 方案

- 模板迁移：`plugins/wakita-governance/agents/*.md` → `plugins/wakita-governance/templates/agents/*.md`（frontmatter 增加 `thoughtLevel: max`、`injectAgentsMd: true`），删除原 `agents/` 目录。
- 脚本改造：`inject-agent-model.py` 目标目录从插件缓存改为 `~/.zcode/agents/`，从模板复制完整文件并注入 `model:`/`thoughtLevel:`；新增 `--thought-level` 参数（默认 max）；保留 --json/--list/--all、provider/model 校验、dry-run、.bak 备份、幂等。
- 命令重写：`commands/subagent-create.md` 交互流程不变（选 provider → 选 model），dry-run/确认后写用户级目录；文档说明「首次运行即初始化生成」。
- 版本：2.3.0 → 2.4.0，同步 4 处（plugin.json / kimi.plugin.json / marketplace.json / AGENTS.md+README.md）。

## 技术要点 ★

### 涉及文件
- `plugins/wakita-governance/agents/` — 删除（3 个 md 移至 templates/agents/ 并改 frontmatter）
- `plugins/wakita-governance/templates/agents/*.md` — 新增（模板，含 thoughtLevel/injectAgentsMd）
- `plugins/wakita-governance/scripts/inject-agent-model.py` — 重写写入逻辑
- `plugins/wakita-governance/scripts/README.md` — 重写用法说明
- `plugins/wakita-governance/commands/subagent-create.md` — 重写执行流程
- `plugins/wakita-governance/kimi.plugin.json` — 移除 `"agents"` 字段、升版本
- `plugins/wakita-governance/.claude-plugin/plugin.json` — 升版本、改 description
- `.claude-plugin/marketplace.json` — 升版本号描述
- `AGENTS.md` / `README.md` — 目录结构、内置子智能体、subagent-create 章节更新
- `plugins/wakita-governance/skills/using-wakita/SKILL.md` — 「模型切换」章节补首次生成说明

### 关键约束
- 模板目录不得命名为插件根下 `agents/`（ZCode 默认扫描该目录，会注册为插件 agent）
- model 值格式不变：`custom:<provider-key>:<model-id>`，provider key 中 `:` 编码为 `%3A`
- `injectAgentsMd: true`（YAML 布尔，非字符串 "Ture"）
- `thoughtLevel` 合法档位由模型元数据决定，`max` 已验证可用（deepseek-v4-flash/pro）
- 写入目标：`Path.home() / ".zcode" / "agents"`（已逆向验证为 ZCode 用户级 subagent 根目录）
- 插件升级前缓存里仍有旧插件级 agent，文档需提示升级后消失

## 备选方案

| 方案 | 优势 | 劣势 | 落选原因 |
|------|------|------|----------|
| 模板嵌入 subagent-create.md，AI 手写文件 | 无脚本依赖 | 命令文件 400+ 行；AI 誊写长文易错 | 可靠性差 |
| 模板嵌入 Python 字符串 | 单文件 | md 混入代码难维护 | 可读性差 |
| 模板独立目录 + 脚本复制（选定） | 单一事实源、保留校验/备份/幂等 | 多一层目录 | — |

## 影响范围

- 插件结构变更（agents/ 删除）；用户已装 2.3.0 需升级 2.4.0 后插件级 agent 才消失
- `/subagent-create` 行为变更：从「改插件缓存」变「写用户目录」
- 不影响 hooks / skills / 其他命令

## 待确认

- [x] 用户级目录 `~/.zcode/agents/` 已被 ZCode 识别（用户已用 dddddddasdddd 验证）
