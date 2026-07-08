# Skill 编写详细指南

> 被 SKILL.md 引用。包含 skill 结构详解、打包资源用途、渐进式披露设计模式与拆分模式、前向测试完整指南。核心规则见 SKILL.md。

## 目录

- [一、Skill 的结构](#一skill-的结构)
- [二、SKILL.md（必需）](#二skillmd必需)
- [三、Agents 元数据（推荐）](#三agents-元数据推荐)
- [四、打包资源（可选）](#四打包资源可选)
- [五、不应包含的文件](#五不应包含的文件)
- [六、渐进式披露设计原则](#六渐进式披露设计原则)
- [七、前向测试完整指南](#七前向测试完整指南)

---

## 一、Skill 的结构

每个 skill 由必需的 SKILL.md 文件和可选打包资源组成：

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
├── agents/ (recommended)
│   └── openai.yaml - UI metadata for skill lists and chips
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation intended to be loaded into context as needed
    └── assets/           - Files used in output (templates, icons, fonts, etc.)
```

---

## 二、SKILL.md（必需）

每个 SKILL.md 由以下部分组成：

- **Frontmatter**（YAML）：包含 `name` 和 `description` 字段。这是 Codex 判断 skill 何时使用的唯一依据，因此清晰、全面地描述 skill 是什么、何时用非常重要。
- **正文**（Markdown）：使用 skill 的指令和指导。仅在 skill 触发后才加载（如果触发的话）。

---

## 三、Agents 元数据（推荐）

- 面向 UI 的元数据，用于 skill 列表和 chip。
- 生成前先读 references/openai.yaml.md，遵循其描述和约束。
- 创建时通过阅读 skill 生成面向人的 `display_name`、`short_description` 和 `default_prompt`。
- 通过 `--interface key=value` 传给 `scripts/generate_openai_yaml.py` 或 `scripts/init_skill.py` 确定性地生成。
- 更新时：验证 `agents/openai.yaml` 是否仍与 SKILL.md 匹配，过期则重新生成。
- 仅当用户明确提供时才包含其他可选界面字段（图标、品牌色）。
- 字段定义和示例见 references/openai.yaml.md。

---

## 四、打包资源（可选）

### Scripts（`scripts/`）

需要确定性可靠性或反复重写的可执行代码（Python/Bash 等）。

- **何时包含**：同一代码被反复重写，或需要确定性可靠性时。
- **示例**：PDF 旋转任务的 `scripts/rotate_pdf.py`。
- **好处**：token 高效、确定性强、可不加载进上下文直接执行。
- **注意**：脚本仍可能需要 Codex 读取以做补丁或环境特定调整。

### References（`references/`）

按需加载进上下文、用于指导 Codex 流程和思考的文档与参考材料。

- **何时包含**：Codex 工作时应参考的文档。
- **示例**：财务 schema 的 `references/finance.md`、公司 NDA 模板的 `references/mnda.md`、公司政策的 `references/policies.md`、API 规范的 `references/api_docs.md`。
- **用例**：数据库 schema、API 文档、领域知识、公司政策、详细工作流指南。
- **好处**：保持 SKILL.md 精简，仅当 Codex 判断需要时才加载。
- **最佳实践**：文件较大（>10k 词）时，在 SKILL.md 中包含 grep 搜索模式。
- **避免重复**：信息应只存在于 SKILL.md 或 references 文件之一，不能两处都有。详细信息优先放 references 文件，除非确实是 skill 核心--这样能保持 SKILL.md 精简，同时让信息可被发现而不挤占上下文窗口。SKILL.md 只保留必要的程序化指令和工作流指导；详细参考材料、schema、示例移到 references 文件。

### Assets（`assets/`）

不加载进上下文、而是用于 Codex 产出的输出中的文件。

- **何时包含**：skill 需要会用在最终输出中的文件时。
- **示例**：品牌资产的 `assets/logo.png`、PowerPoint 模板的 `assets/slides.pptx`、HTML/React 样板的 `assets/frontend-template/`、字体的 `assets/font.ttf`。
- **用例**：模板、图片、图标、样板代码、字体、被复制或修改的样本文档。
- **好处**：把输出资源与文档分离，使 Codex 能使用文件而不加载进上下文。

---

## 五、不应包含的文件

skill 应只包含直接支撑其功能的必要文件。**不要**创建多余文档或辅助文件，包括：

- README.md
- INSTALLATION_GUIDE.md
- QUICK_REFERENCE.md
- CHANGELOG.md
- 等等

skill 应只包含 AI agent 完成手头任务所需的信息，不应包含创建过程的辅助上下文、安装测试流程、面向用户的文档等。创建额外文档文件只会增加混乱。

---

## 六、渐进式披露设计原则

Skills 使用三层加载系统高效管理上下文：

1. **元数据（name + description）** - 始终在上下文中（约 100 词）
2. **SKILL.md 正文** - skill 触发时加载（<5k 词）
3. **打包资源** - 按 Codex 需要加载（无限制，因为脚本可不读进上下文直接执行）

### 渐进式披露模式

保持 SKILL.md 正文精炼、在 500 行以内以减少上下文膨胀。接近此限制时把内容拆分到单独文件。拆分时，在 SKILL.md 中引用并清晰描述何时读取它们非常重要，以确保 skill 读者知道它们的存在和使用时机。

**关键原则：** 当 skill 支持多种变体、框架或选项时，SKILL.md 只保留核心工作流和选择指导。把变体特定的细节（模式、示例、配置）移到单独的参考文件。

#### 模式 1：带参考的高级指南

```markdown
# PDF Processing

## Quick start

Extract text with pdfplumber:
[code example]

## Advanced features

- **Form filling**: See [FORMS.md](FORMS.md) for complete guide
- **API reference**: See [REFERENCE.md](REFERENCE.md) for all methods
- **Examples**: See [EXAMPLES.md](EXAMPLES.md) for common patterns
```

Codex 仅在需要时加载 FORMS.md、REFERENCE.md 或 EXAMPLES.md。

#### 模式 2：按领域组织

对于多领域 skill，按领域组织内容以避免加载无关上下文：

```
bigquery-skill/
├── SKILL.md (overview and navigation)
└── reference/
    ├── finance.md (revenue, billing metrics)
    ├── sales.md (opportunities, pipeline)
    ├── product.md (API usage, features)
    └── marketing.md (campaigns, attribution)
```

当用户问销售指标时，Codex 只读 sales.md。类似地，支持多框架或变体的 skill 按变体组织：

```
cloud-deploy/
├── SKILL.md (workflow + provider selection)
└── references/
    ├── aws.md (AWS deployment patterns)
    ├── gcp.md (GCP deployment patterns)
    └── azure.md (Azure deployment patterns)
```

当用户选 AWS 时，Codex 只读 aws.md。

#### 模式 3：条件细节

展示基础内容，链接到高级内容：

```markdown
# DOCX Processing

## Creating documents

Use docx-js for new documents. See [DOCX-JS.md](DOCX-JS.md).

## Editing documents

For simple edits, modify the XML directly.

**For tracked changes**: See [REDLINING.md](REDLINING.md)
**For OOXML details**: See [OOXML.md](OOXML.md)
```

Codex 仅在用户需要这些功能时读 REDLINING.md 或 OOXML.md。

### 重要准则

- **避免深层嵌套引用** - references 保持离 SKILL.md 一层深。所有参考文件应直接从 SKILL.md 链接。
- **为较长的参考文件建立结构** - 超过 100 行的文件，顶部放目录，让 Codex 预览时能看到全貌。

---

## 七、前向测试完整指南

前向测试通过启动 subagent 对 skill 做最小上下文的压力测试。subagent **不应知道**自己在被要求测试 skill，应被当作被用户要求执行任务的 agent 对待。给 subagent 的提示应像：
```
Use $skill-x at /path/to/skill-x to solve problem y
```
而非：
```
Review the skill at /path/to/skill-x; pretend a user asks you to...
```

### 前向测试决策规则

- 倾向于前向测试。
- 若认为前向测试可能：耗时较长、需要用户额外批准、或修改线上生产系统，则先征求同意。此时把拟用提示和请求展示给用户，请其给（1）是/否决定，以及（2）任何修改建议。

### 前向测试注意事项

- 为独立的验证用新线程。
- 以与用户类似的方式传递 skill 和请求。
- 传递原始素材，而非你的结论。
- 避免展示预期答案或预期修复。
- 每次迭代后从原始素材重建上下文。
- 审查 subagent 的输出、推理和产出的素材。
- 避免在迭代间留下 agent 能在磁盘上找到的素材；清理 subagent 的素材以避免额外污染。

### 前向测试与迭代工作流

1. 在真实任务上使用 skill。
2. 注意挣扎或低效之处。
3. 识别 SKILL.md 或打包资源应如何更新。
4. 实施改动并再次测试。
5. 合理且适当时做前向测试。

如果前向测试只有当 subagent 看到泄露上下文才成功，则在信任结果前收紧 skill 或前向测试设置。

### 保护验证完整性

使用 subagent 迭代验证 skill 在真实任务上是否有效时，把它当作评估面。目标是学习 skill 是否泛化，而非另一个 agent 能否从泄露的上下文重建答案。优先用原始素材（示例提示、输出、diff、日志、trace），只给完成任务所需的最小局部上下文。避免传递预期答案、疑似 bug、预期修复或你的既有结论，除非验证明确需要。
