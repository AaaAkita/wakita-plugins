---
name: "openai-docs"
description: "当用户询问如何基于 OpenAI 产品或 API 进行构建、询问 Codex 本身或选择 Codex 各产品形态、需要带引用的最新官方文档、为某个用例选择最新模型、或需要模型升级与 prompt 升级指引时使用；非 Codex 文档问题使用 OpenAI docs MCP 工具；广泛的 Codex 自身知识优先使用 Codex manual 辅助工具；回退浏览仅限 OpenAI 官方域名。"
---


# OpenAI Docs

基于 developers.openai.com MCP 服务器，提供来自 OpenAI 开发者文档的权威、最新指引。"Docs MCP" 指 `mcp__openaiDeveloperDocs__search_openai_docs` 与 `mcp__openaiDeveloperDocs__fetch_openai_doc`；对于 API 参考、schema、参数或必填字段相关问题，在可用时还需使用 `mcp__openaiDeveloperDocs__get_openapi_spec`。当上述工具不可用或无帮助时，回退到官方域名 web 搜索作为兜底。广泛的 Codex 问题优先使用 manual 辅助工具，再走 Docs MCP。本 skill 还负责模型选择、API 模型迁移与 prompt 升级指引。

## API Key 设置

对于构建、运行、配置、调试或实现基于 API 的应用、脚本、CLI、生成器或工具的请求，在可用时优先使用 `openai-platform-api-key`。该凭据门禁解决后，再按需回到此处获取最新文档。

对于纯文档问题、引用、模型/API 指引、概念解释以及无需构建或运行基于 API 产物的示例，直接使用本 skill。

## 工作流配置

### 来源优先级

- 对于 Codex 自身知识，使用下文的 Codex 来源路线；它决定何时使用 manual 辅助工具、Docs MCP 或有界不确定性（bounded uncertainty）。
- 对于非 Codex 的 OpenAI 文档问题，使用 `mcp__openaiDeveloperDocs__search_openai_docs` 查找最相关的文档页面。
- 对于非 Codex 的 OpenAI 文档问题，回答前用 `mcp__openaiDeveloperDocs__fetch_openai_doc` 拉取相关页面。若搜索结果噪声大，运行更窄的 Docs MCP 搜索；当已知或找到任何貌似官方 OpenAI 文档 URL 时，优先通过 Docs MCP 尝试拉取该 URL，再依赖 web 搜索内容。
- 对于 API 参考、schema、参数或必填字段问题，在可用时使用 `mcp__openaiDeveloperDocs__get_openapi_spec` 在相关 guide 或 reference 页面旁验证 API 形状。
- 仅当需要无明确查询地浏览或发现非 Codex 页面时，才使用 `mcp__openaiDeveloperDocs__list_openai_docs`。
- 对于模型选择、"latest model" 或默认模型问题，优先拉取 `https://developers.openai.com/api/docs/guides/latest-model.md`。若不可用，加载 `references/latest-model.md`。
- 对于模型升级或 prompt 升级，仅当目标为 latest/current/default 或其他未明确指定时，运行 `node scripts/resolve-latest-model-info.js`；否则保留显式指定的目标。
- 保留显式目标请求：若用户点名某个目标模型如 "migrate to GPT-5.4"，即使 `latest-model.md` 列出了更新的模型，也保留该请求目标。仅将更新指引作为可选项提及。
- 若需要当前远程指引，直接拉取返回的迁移与 prompting guide 两个 URL。若直接拉取失败，使用 MCP/搜索回退；若仍失败，使用内置回退参考并说明已使用回退。

## OpenAI 产品快照

1. Apps SDK：通过提供 web component UI 和向 ChatGPT 暴露应用工具的 MCP server 来构建 ChatGPT 应用。
2. Responses API：为 agentic 工作流中有状态、多模态、使用工具的交互设计的统一端点。
3. Chat Completions API：从构成一段对话的消息列表生成模型响应。
4. Codex：OpenAI 面向软件开发的编码 agent，能编写、理解、审查和调试代码。
5. gpt-oss：OpenAI 在 Apache 2.0 许可下发布的开放权重推理模型（gpt-oss-120b 和 gpt-oss-20b）。
6. Realtime API：构建低延迟、多模态体验，包括自然的语音到语音对话。
7. Agents SDK：用于构建 agentic 应用的工具包，模型可使用工具和上下文、交接给其他 agent、流式返回部分结果并保留完整 trace。

## Codex 自身知识

对于关于 Codex 本身的问题使用此路径：配置、扩展、运行、排障、本地状态、产品形态、或 Codex 行为应归属何处。代码库仅提及某个插件、skill、hook、MCP server、浏览器或自动化不足以触发本路径。对于通用软件任务，直接回答该软件任务；若被问及 Codex 自身知识是否适用，简要回答该元问题后继续完成请求的产物。

### 来源路线

Codex manual 是广泛 Codex 综合问题的第一来源。将 manual 与 Docs MCP 视为不同通道，而非可互换的官方文档来源。对于已发布用户层面的 Codex 产品回答，来源路线是完整的：manual、本路线需要的 Docs MCP、官方 OpenAI web 回退、以及当问题涉及某项能力时当前会话中已呈现的可调用能力。developers.openai.com 之外的知识库不在公开产品回答的本路线内。

对于广泛的 Codex 行为、设置、定制、skills、plugins、MCP、hooks、`AGENTS.md`、automations、产品形态、本地状态或系统图问题：

1. 当同一线程的 manual 与 outline 路径仍然新鲜时，复用它们。
2. 否则在普通可写会话中优先运行 skill 本地辅助工具。仅当会话明确只读、shell 执行不可用、或可见策略显示无允许的临时缓存时，才跳过它而不尝试。
3. 默认情况下，辅助工具按以下顺序选择第一个可用的临时缓存目录：`$TMPDIR/openai-docs-cache`、`%TEMP%\openai-docs-cache`、`%TMP%\openai-docs-cache`、`/private/tmp/openai-docs-cache`，然后 `/tmp/openai-docs-cache`。仅工作区可写权限不足以满足此临时缓存需求。
4. 直接运行辅助工具，除非需要覆盖缓存目录。当原生 `fetch` 不可用或存在代理环境变量时，辅助工具回退到 `curl`，因此不需要 shell 特定的代理前缀。将 `<skill-dir>` 解析为本 skill 的实际目录；在复制的本地 eval 工作目录中通常是 `.codex/skills/openai-docs`：

```bash
node <skill-dir>/scripts/fetch-codex-manual.mjs
```

如需覆盖缓存目录，传入 `--cache-dir <cache-dir>`。在 Windows 上，辅助工具会自动检查 `%TEMP%` 和 `%TMP%`；在 PowerShell 中，`$env:TEMP\\openai-docs-cache` 是典型的显式覆盖。

将辅助工具的可用性视为由显式只读/无 shell 策略或实际命令结果确立。猜测的沙箱或猜测的辅助工具失败不足以切换到 Docs MCP 或 web 查找；在实际辅助工具命令失败后，继续到下文最窄的官方下一来源。

辅助工具验证新鲜度，写入 `codex-manual.md`，并输出 `codex-manual.outline.md`。outline 将来源页面和标题映射到行范围；用它选择相关 manual 章节，然后读取或搜索目标 manual 章节以获取 Codex 产品事实。使用 skill 目录定位并运行辅助工具；辅助工具成功后，使用返回的 manual 和 outline 路径作为 Codex 产品事实与术语覆盖检查的搜索范围。

对于后续 Codex 问题，复用同一线程的 manual 和 outline 路径。当 manual 拉取超过约一天、路径不可用、路径来自其他线程或来源不确定、或可能缺失当前信息且陈旧可信时，先刷新。

对于 manual 是否足够新鲜可现在依赖的问题，在允许临时缓存时运行辅助工具，并基于其返回状态、manual 路径和 outline 路径作答。

若 manual 解决了某个 Codex 声明，从其作答并停止为该声明扩展来源；若文档查找只是一个依赖项，则继续用户更广泛的任务。manual 来源页面与已知锚点对 manual 覆盖的材料足够作为引用支撑。

若因会话只读、无 shell 执行或无允许的临时缓存而跳过辅助工具，下一来源是 Docs MCP：在任何 web 回退之前，调用 `mcp__openaiDeveloperDocs__search_openai_docs`，然后对相关命中调用 `mcp__openaiDeveloperDocs__fetch_openai_doc`。

若用户点名某个新鲜 manual 未使用的 Codex 术语或模式，在 manual 中搜索明显的相邻概念，然后回答该确切术语未文档化并使用最接近的文档化术语。若 prompt 询问该术语如何映射到 Codex 行为，从相邻 manual 章节解析该映射。若该确切术语在那次 manual 过扫后仍然实质性或可能当前，在有界不确定性之前使用一次窄 Docs MCP 搜索/拉取；否则该术语或映射声明的来源查找完成。

仅当 manual 不可用、辅助工具失败、不允许临时缓存、另一项实质性声明缺失或可能陈旧、或用户明确需要页面级引用时，才使用最窄的官方下一来源。优先一次具体的 Docs MCP 搜索，若返回明显相关页面则一次拉取；对于未解决的 Codex 能力名、缩写、调度术语或确切错误文本，此 Docs MCP 步骤是 web 搜索之前的下一来源。在 manual 加任何允许的 Docs MCP 填补之后，将剩余缺口解析为有界不确定性。仅当该 Docs MCP 路径不可用或无帮助时，使用官方域名 web 回退。若声明仍未确立，以有界不确定性停止。若官方文档/manual 与当前会话中已呈现的可调用能力冲突，说明冲突并优先该环境中已验证的当前会话行为。

对于未文档化或看似私有的 model slug、产品模式标签、权益标签、账户访问路径或 rollout 名称，从当前公开文档与有界不确定性作答。这些标签不是离开公开来源路线的理由。

对于支持式诊断，优先从 manual 给出分层回答，而非特定提供商的 web 查找：已安装/已启用的插件、bundled app 或 connector 授权、MCP 设置、工作区/管理员策略、重启或新线程预期，然后仍未解决则转支持或反馈。

若来源路线仍未确立某声明，返回有界不确定性或转支持、管理员或产品反馈，而不是扩大调查范围。

对于未解决的产品术语，从 manual 加允许的官方下一来源作答。若这些来源未确立该术语，以这些来源的有界不确定性作答。

### 形态图

当 Codex 名词或持久指令形态重叠时，推荐匹配范围的最小形态：

- Prompt 或 thread context -> 一次性任务约束。
- `AGENTS.md` -> 持久仓库约定、命令、验证步骤和审查期望；更近的嵌套文件在其子树下适用。
- 项目 `.codex/config.toml` -> 受信任仓库的 Codex 设置，如 sandbox、MCP、hooks、model 或 reasoning 默认值。
- 全局 config 或全局指引 -> 跨仓库的个人默认值。
- Skill -> 带 references 或 scripts 的可复用任务工作流。
- Plugin -> 带 skills 以及 commands、tools、MCP config、hooks、assets、apps 或 marketplace 元数据的可安装包。
- MCP server 或 app connector -> 实时外部数据/操作或已授权的私有应用/工作区数据。对于私有 Google Docs、Calendar、Slack、GitHub、Notion 及类似数据，使用 connector 而非 web 搜索或模型记忆。
- Automation -> 计划检查、提醒、监控或后续工作；当在已有线程中保持连续性重要时，使用线程心跳。
- Hook -> 围绕工具调用、命令或文件编辑的生命周期强制。

拆分混合范围请求，而非强行给一个答案。示例："always do X, but only for this PR" 默认对当前运行使用 prompt/thread context；仅当应持久化时使用 `AGENTS.md` 或项目 config，仅用于机械强制时使用 hooks，仅用于计划或后续工作时使用 automations。

需要时使用此快速产品图：CLI 是终端优先的本地仓库工作；IDE extension 是编辑器附连的编码；Codex app 是桌面规划、审查和交互式工作；cloud/web 是托管的并行/卸载工作；Browser Use/应用内浏览器是 Codex 控制的 web 测试；Chrome extension 使用用户的 Chrome 配置；Computer Use 控制桌面应用和 OS UI。将 `config.toml` 默认值、`requirements.toml` 约束和托管/管理员策略分开。

### 边界与输出

- API key 认证不意味着 ChatGPT、cloud task 或 connector 访问。对于 plugin/app/auth 失败，回答前检查 bundle 可用性、插件已安装/已启用状态、connector/app 授权、MCP 设置、重启/刷新预期、工作区策略和各形态可用性。
- 沙箱或网络拒绝需要带清晰理由的有界升级。破坏性命令、工作区外写入或广泛访问变更需要显式批准。
- Memory 可提供用户偏好或上下文，但显式 prompt 指令优先，且 memory 不是当前外部事实的来源。
- 对于肯定性形态选择回答，使用此形状：推荐、原因、应避免什么、以及所用的 manual/来源证据。
- 当确实需要页面级 Codex 引用时，这些锚点通常适用：`concepts/customization#agents-guidance` 用于 `AGENTS.md`，`concepts/customization#skills` 用于 skills，`plugins/build#plugin-structure` 用于 plugins，`concepts/customization#mcp` 用于 MCP，`config-advanced#hooks` 用于 hooks，`app/automations#thread-automations` 用于 thread automations，`config-reference#configtoml` 用于 config。

## 若 MCP server 缺失

若 MCP 工具失败或无 OpenAI docs 资源可用：

1. 自行运行安装命令：`codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp`
2. 若因权限/沙箱失败，立即以提升权限重试同一命令，并附一句批准理由。
3. 仅当提升尝试失败时，才请用户运行安装命令。
4. 请用户重启 Codex。
5. 重启后重新运行文档搜索/拉取。

## 工作流

1. 澄清请求是通用文档查找、模型选择、model-string 升级、prompt 升级指引，还是更广泛的 API/提供商迁移。
2. 对于 Codex 自身知识请求，遵循上文 Codex 自身知识来源流程。
3. 对于模型选择或升级请求，当用户询问 latest/current/default 指引时，优先使用当前远程文档而非内置参考。
   - 拉取 `https://developers.openai.com/api/docs/guides/latest-model.md`。
   - 查找最新 model ID 和显式的迁移或 prompt-guidance 链接。
   - 优先使用 latest-model 页面的显式链接而非推导的 URL。
   - 对于显式点名的模型请求，保留请求的模型目标。仅将更新的远程指引作为可选项提及。
   - 对于动态的 latest/current/default 升级，运行 `node scripts/resolve-latest-model-info.js`，然后在可能时直接拉取返回的两个 guide URL。
   - 若直接 guide 拉取失败，使用 developer-docs MCP 工具或官方 OpenAI 域名搜索查找相同的 guide 内容。
   - 若远程文档不可用，使用内置回退参考并说明已使用回退指引。
4. 对于模型升级，保持改动窄：仅在安全时更新活跃的 OpenAI API model 默认值和直接相关的 prompt。
5. 除非用户明确要求升级，否则保持历史文档、示例、eval 基线、fixtures、提供商比较、提供商注册表、定价表、别名默认值、低成本回退路径和模糊的旧模型用法不变。
6. 除非用户明确要求，否则将 SDK、工具、IDE、插件、shell、auth 和提供商环境的迁移排除在模型与 prompt 升级之外。
7. 若升级需要 API 表面变更、schema 重接、tool-handler 变更或超出字面 model-string 替换和 prompt 编辑的实现工作，报告为受阻或需确认。
8. 对于通用文档查找，用精确查询搜索文档，拉取所需最佳页面和确切章节，并以简洁引用作答。

## 参考映射

仅按需读取：

- `https://developers.openai.com/api/docs/guides/latest-model.md` -> 当前模型选择与 "best/latest/current model" 问题。
- `scripts/fetch-codex-manual.mjs` -> 当前 Codex manual 拉取、验证、本地临时缓存和 outline 生成。
- `https://developers.openai.com/codex/codex-manual.md` -> 当前 Codex 自身知识综合，包括设置、定制、skills、plugins、MCP、hooks、`AGENTS.md`、automations 和形态行为；通常在临时缓存可用时通过辅助工具路径和目标文件读取访问。
- `references/latest-model.md` -> 模型选择与 "best/latest/current model" 问题的内置回退。
- `references/upgrade-guide.md` -> 模型升级和升级规划请求的内置回退。
- `references/prompting-guide.md` -> prompt 重写和 prompt 行为升级的内置回退。

## 质量规则

- 将 OpenAI 文档视为事实来源；避免猜测。
- 对于 Codex 自身知识，遵循上文来源路线，而非依赖记忆的行为。
- 保持迁移改动窄且行为保留。
- 可能时优先仅 prompt 升级。
- 避免编造定价、可用性、参数、API 变更或破坏性变更。
- 保持引用简短并在策略限制内；优先带引用的复述。
- 若多个页面有差异，指出差异并两者都引用。
- 若官方文档与已验证的当前会话可调用行为不一致，在做出广泛声明或编辑前说明冲突。
- 若文档未覆盖用户需求，明确说明并提供下一步。

## 工具说明

- 对于 OpenAI 相关 markdown 文档，在 web 搜索之前使用 MCP 文档工具。Codex manual 流程是例外：对于广泛的 Codex 综合，遵循 Codex 自身知识来源流程。
- 若 MCP server 已安装但返回无意义结果，则使用 web 搜索作为回退。
- 当回退到 web 搜索时，限制在官方 OpenAI 域名（developers.openai.com、platform.openai.com）并引用来源。
