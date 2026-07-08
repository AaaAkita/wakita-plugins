---
name: skill-creator
description: 创建 skill 的指南。当用户想创建新 skill（或更新已有 skill），以扩展 ZCode 能力、提供专门知识、工作流或工具集成时，使用本 skill。
metadata:
  short-description: Create or update a skill
---

# Skill 创建器

本 skill 提供创建有效 skill 的指导。

## 关于 Skills

Skills 是模块化、自包含的文件夹，通过提供专门的知识、工作流和工具来扩展 ZCode 的能力。可把它们视为特定领域或任务的"入职指南"--它们把 ZCode 从通用 agent 转变为具备程序化知识（任何模型都无法完全具备）的专用 agent。

### Skills 提供什么

1. 专门工作流 - 特定领域的多步骤流程
2. 工具集成 - 操作特定文件格式或 API 的指令
3. 领域专长 - 公司特定知识、schema、业务逻辑
4. 打包资源 - 复杂、重复任务的脚本、参考文档和素材

## 核心原则

### 简洁至上

上下文窗口是公共资源。Skills 与 ZCode 需要的其他内容（系统提示、对话历史、其他 Skills 元数据、用户请求）共享上下文窗口。

**默认假设：ZCode 已经很聪明。** 只添加 ZCode 还不知道的内容。对每条信息都质疑："ZCode 真的需要这个解释吗？"、"这段文字值得它的 token 开销吗？" 优先用简洁的示例而非冗长的解释。

### 设置合适的自由度

把指令的具体程度与任务的脆弱性和可变性相匹配：

- **高自由度（文本指令）**：多种方法都可行、决策依赖上下文、用启发式引导时使用。
- **中自由度（伪代码或带参数脚本）**：存在首选模式、可接受一定变化、配置影响行为时使用。
- **低自由度（具体脚本、少参数）**：操作脆弱易错、一致性关键、必须遵循特定顺序时使用。

把 ZCode 想象成在探索路径：悬崖边的窄桥需要明确护栏（低自由度），开阔田野则允许很多路线（高自由度）。

### 保护验证完整性

迭代时可使用 subagent 验证 skill 在真实任务上是否有效，或某个可疑问题是否真实存在。这在修订后想对 skill 的行为、输出或失败模式做独立验证时最有用。仅当能启动新 subagent 时才这样做。

用 subagent 验证时，把它当作评估面。目标是学习 skill 是否泛化，而非另一个 agent 能否从泄露的上下文重建答案。优先用原始素材（示例提示、输出、diff、日志、trace），只给完成任务所需的最小局部上下文。避免传递预期答案、疑似 bug、预期修复或你的既有结论，除非验证明确需要。

### Skill 的结构

每个 skill 由必需的 SKILL.md 文件和可选打包资源组成。结构、字段定义、打包资源（scripts/references/assets）用途与"渐进式披露"设计模式（三层加载：元数据/SKILL.md 正文/打包资源）详见 `references/skill-authoring-guide.md`。

## Skill 创建流程

创建 skill 涉及以下步骤，按顺序执行，仅在明确不适用时跳过：

1. **用具体示例理解 skill** - 搞清楚 skill 如何被使用的具体示例。可来自用户直接示例或经用户反馈验证的生成示例。避免一次问太多问题，从最重要的开始，按需跟进。
2. **规划可复用内容** - 分析每个示例：从零开始怎么执行；重复执行时哪些脚本、参考文档、素材会有帮助。据此列出要包含的可复用资源。
3. **初始化 skill** - 运行 `init_skill.py` 生成模板目录。运行前询问用户想在哪里创建，默认 `$ZCODE_HOME/skills`（`ZCODE_HOME` 未设时回退到 `~/.zcode/skills` 以便自动发现）。已有 skill 跳过本步。
4. **编辑 skill** - 先实现可复用资源（scripts/references/assets），再更新 SKILL.md。脚本必须实际运行测试。大幅修订或 skill 较复杂时，用 subagent 对真实任务做前向测试。
5. **验证 skill** - 运行 `scripts/quick_validate.py <path/to/skill-folder>` 检查 YAML frontmatter 格式、必填字段、命名规则。失败则修复后重跑。
6. **迭代** - 在真实任务上使用 skill，发现问题后更新 SKILL.md 或打包资源并再次测试，必要时前向测试。

### Skill 命名

- 只用小写字母、数字、连字符；用户提供的标题规范化为连字符形式（如 "Plan Mode" -> `plan-mode`）。
- 生成名字时控制在 64 字符以内（字母、数字、连字符）。
- 优先用简短、动词引导的短语描述动作。
- 工具名作为命名空间可提升清晰度或触发率（如 `gh-address-comments`、`linear-address-issue`）。
- skill 文件夹名与 skill 名完全一致。

### 初始化脚本用法

```bash
scripts/init_skill.py <skill-name> --path <output-directory> [--resources scripts,references,assets] [--examples]
```

示例：

```bash
scripts/init_skill.py my-skill --path "${ZCODE_HOME:-$HOME/.zcode}/skills"
scripts/init_skill.py my-skill --path "${ZCODE_HOME:-$HOME/.zcode}/skills" --resources scripts,references
scripts/init_skill.py my-skill --path ~/work/skills --resources scripts --examples
```

脚本会创建 skill 目录、生成带 frontmatter 和 TODO 占位符的 SKILL.md 模板、用 `--interface key=value` 传入的 `display_name`/`short_description`/`default_prompt` 创建 `agents/openai.yaml`、按 `--resources` 创建资源目录、`--examples` 时加示例文件。初始化后自定义 SKILL.md 并添加资源，用了 `--examples` 则替换或删除占位文件。

用 `scripts/generate_openai_yaml.py <path/to/skill-folder> --interface key=value` 可重新生成 openai.yaml。仅当用户明确提供时才包含其他可选界面字段。字段定义见 `references/openai_yaml.md`。

### 编辑 SKILL.md 的写作要点

**始终用祈使句/不定式形式。**

frontmatter 写 `name` 和 `description`：
- `name`：skill 名。
- `description`：skill 的主要触发机制，帮助 ZCode 理解何时使用。要包含 skill 做什么 + 何时使用的具体触发条件/上下文。所有"何时使用"信息放这里，不放正文（正文在触发后才加载，正文里的"何时使用本 skill"章节对 ZCode 无用）。frontmatter 不要包含其他字段。

正文写使用 skill 及其打包资源的指令。

## 前向测试

前向测试通过启动 subagent 来对 skill 做最小上下文的压力测试。subagent **不应知道**自己在测试 skill，应被当作被用户要求执行任务的 agent。给 subagent 的提示应像：`Use $skill-x at /path/to/skill-x to solve problem y`，而非 `Review the skill at /path/to/skill-x; pretend a user asks you to...`。

决策规则：倾向于前向测试；若认为前向测试可能耗时较长、需要用户额外批准、或修改线上生产系统，则先征得同意--把拟用提示和请求展示给用户，请其给是/否决定及任何修改建议。

前向测试注意事项、详细的前向测试与迭代工作流见 `references/skill-authoring-guide.md`。

## 参考文档

- [skill-authoring-guide.md](references/skill-authoring-guide.md) - Skill 结构详解、打包资源（scripts/references/assets）用途、渐进式披露设计模式与拆分模式、前向测试完整指南
- [openai_yaml.md](references/openai_yaml.md) - agents/openai.yaml 字段定义与示例
