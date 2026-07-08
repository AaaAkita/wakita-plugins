---
name: "imagegen"
description: "当任务受益于 AI 创建的位图视觉（如照片、插画、纹理、精灵图、样机或透明背景抠图）时，生成或编辑光栅图像。当 Codex 应创建全新图像、变换现有图像、或从参考图派生视觉变体，且输出应为位图素材而非仓库原生代码或矢量时使用。当任务更适合编辑现有 SVG/矢量/代码原生素材、扩展现有图标或 logo 系统、或直接用 HTML/CSS/canvas 构建视觉时，不要使用本 skill。"
---

# 图像生成 Skill

为当前项目生成或编辑图像（例如网站素材、游戏素材、UI 样机、产品样机、线框图、logo 设计、写实照片或信息图）。

## 顶层模式与规则

本 skill 恰好有两个顶层模式：

- **默认内置工具模式（首选）**：内置 `image_gen` 工具，用于常规图像生成、编辑和简单透明图请求。不需要 `OPENAI_API_KEY`。
- **回退 CLI 模式**：`scripts/image_gen.py` CLI。当用户明确要求 CLI/API/模型路径时使用，或在用户明确确认使用 `gpt-image-1.5` 的真正模型原生透明回退后使用。需要 `OPENAI_API_KEY`。

CLI 回退下暴露三个子命令：`generate`、`edit`、`generate-batch`。

规则：
- 常规图像生成和编辑请求默认用内置 `image_gen` 工具。
- 不要因普通的质量、尺寸或文件路径控制切换到 CLI 回退。
- 若用户明确要求透明图像/背景，先用内置 `image_gen`：提示生成纯色可移除色键背景，再用已安装的 helper `$CODEX_HOME/skills/.system/imagegen/scripts/remove_chroma_key.py` 本地移除。
- 绝不在未告知用户的情况下从内置 `image_gen` 或 CLI `gpt-image-2` 切换到 CLI `gpt-image-1.5`。视其为模型/路径降级，除非用户已明确要求 `gpt-image-1.5`、`scripts/image_gen.py` 或 CLI 回退，否则切换前先询问用户。
- 若透明请求对干净色键移除过于复杂、要求真正/原生透明、或本地移除验证失败，说明真正透明需要 CLI `gpt-image-1.5 --background transparent --output-format png`（因 `gpt-image-2` 不支持 `background=transparent`），然后询问是否继续。仅在用户确认后运行 CLI 回退。
- "batch"一词本身不意味着 CLI 回退。若用户要很多素材或说批量生成但未明确要求 CLI/API/模型控制，留在内置路径，每个请求的素材或变体发一次内置调用。
- 若内置工具失败或不可用，告诉用户存在 CLI 回退且需要 `OPENAI_API_KEY`。仅在用户明确要求该回退时才继续。
- 若用户明确要求 CLI 模式，用打包的 `scripts/image_gen.py` 工作流。不要创建一次性 SDK runner。
- 绝不修改 `scripts/image_gen.py`。若缺少功能，先问用户再做其他事。

内置保存路径策略：内置工具模式下 Codex 默认把生成图像保存在 `$CODEX_HOME/*` 下。不要把 OS 临时目录描述或当作默认内置目标。不要描述或依赖内置 `image_gen` 工具上（若有）的目标路径参数。若需特定位置，先生成再把选中输出从 `$CODEX_HOME/generated_images/...` 移动或复制。保存路径优先级：1) 用户指定目标则移动/复制到该处；2) 图像用于当前项目则把最终选中图像移入工作区再结束；3) 仅预览或头脑风暴则内联渲染，底层文件可留在默认 `$CODEX_HOME/*` 路径。绝不把项目引用的素材只留在默认 `$CODEX_HOME/*` 路径。除非用户明确要求替换，否则不要覆盖已有素材；否则创建同级带版本号的文件名如 `hero-v2.png` 或 `item-icon-edited.png`。

两种模式共享的提示词指南见 `references/prompting.md` 和 `references/sample-prompts.md`。仅 CLI 模式的回退文档/资源：`references/cli.md`、`references/image-api.md`、`references/codex-network.md`、`scripts/image_gen.py`。本地后处理 helper：`$CODEX_HOME/skills/.system/imagegen/scripts/remove_chroma_key.py`（从生成图像移除纯色色键背景并写入带 alpha 的 PNG/WebP，优先用自动键采样、软遮罩和 despill 处理抗锯齿边缘）。

## 何时使用

- 生成新图像（概念图、产品照、封面、网站 hero）
- 用一张或多张参考图生成新图像（用于风格、构图或氛围）
- 编辑现有图像（inpainting、光照或天气变换、背景替换、对象移除、合成、透明背景）
- 为一个任务产出很多素材或变体

## 何时不使用

- 扩展或匹配仓库内已有的 SVG/矢量图标集、logo 系统或插画库
- 创建更适合直接用 SVG、HTML/CSS 或 canvas 生产的简单形状、图表、线框图或图标
- 源文件已存在可编辑原生格式时做项目内小素材编辑
- 用户明显想要确定性代码原生输出而非生成位图的任何任务

## 决策树

考虑两个独立问题：

1. **意图**：是新图像还是编辑现有图像？
2. **执行策略**：单个素材还是多个素材/变体？

意图：用户想修改现有图像同时保留其部分 -> **edit**；用户提供图像仅作风格/构图/氛围/主体参考 -> **generate**；用户未提供图像 -> **generate**。

内置编辑语义：内置编辑模式用于对话上下文中已可见的图像（如附件或线程中早先生成的图像）。用户想用内置工具编辑本地图像文件时，先用内置 `view_image` 工具加载使其在对话上下文中可见，再走内置编辑流程。不要承诺通过内置工具做任意文件系统路径编辑。若本地文件仍需直接文件路径控制、遮罩或其他显式 CLI 专属参数，仅在用户要求时用显式 CLI 回退。编辑时积极保持不变量，默认非破坏性保存。

执行策略：内置默认路径下，每个请求的素材或变体发一次 `image_gen` 调用来产出多个素材或变体。CLI 回退路径下，仅当用户明确选择 CLI 模式且需要很多提示/素材时用 CLI `generate-batch` 子命令。对于很多不同素材，不要用 `n` 替代独立提示。`n` 用于一个提示的变体；不同素材需要不同的内置调用或不同 CLI `generate-batch` 作业。

除非用户明确要求改现有图像，否则假设用户想要新图像。

## 工作流

1. 决定顶层模式：默认内置（含简单透明输出请求）；仅当明确要求或用户明确确认透明回退时用回退 CLI。
2. 决定意图：`generate` 或 `edit`。
3. 决定输出仅预览还是供当前项目使用。
4. 决定执行策略：单个素材 vs 重复内置调用 vs CLI `generate-batch`。
5. 预先收集输入：提示、精确文本（逐字）、约束/避免列表、任何输入图像。
6. 为每张输入图像明确标注角色：参考图、编辑目标、辅助插入/风格/合成输入。
7. 若编辑目标仅在本地文件系统且留在内置路径，先用 `view_image` 检查使其在对话上下文中可用。
8. 若用户要照片、插画、精灵图、产品图、banner 或其他显式光栅风格素材，用 `image_gen` 而非 SVG/HTML/CSS 占位符替代。若请求是图标、logo 或应匹配仓库现有 SVG/矢量/代码素材的 UI 图形，优先直接编辑那些素材。
9. 按具体性增强提示：提示已具体详细则规范化为清晰规范，不加创意要求；提示宽泛则仅在能实质改善输出质量时做有品味的增强。
10. 默认用内置 `image_gen` 工具。
11. 透明输出请求遵循透明图像指南（见 `references/workflow-details.md`）：用内置 `image_gen` 在纯色色键背景上生成，把选中输出复制进工作区或 `tmp/imagegen/`，运行已安装 helper 移除色键并验证 alpha 结果。若路径不合适或失败，切换 CLI `gpt-image-1.5` 前先询问。
12. 检查输出并验证：主体、风格、构图、文本准确性、不变量/避免项。
13. 用单次针对性改动迭代，再重新检查。
14. 仅预览工作内联渲染；底层文件可留在默认 `$CODEX_HOME/generated_images/...` 路径。
15. 项目绑定工作把选中素材移入工作区并更新任何消费代码或引用。绝不把项目引用的素材只留在默认路径。
16. 批量或多素材请求把每个请求的最终交付物持久化到工作区，除非用户明确要求仅保留预览。被丢弃的变体无需保留，除非用户要求。
17. 用户明确选择或确认 CLI 回退时，用仅回退文档查模型、质量、尺寸、`input_fidelity`、遮罩、输出格式、输出路径、网络设置。
18. 始终报告任何工作区绑定素材的最终保存路径，以及最终提示/提示集和用的是内置工具还是回退 CLI 模式。

## 提示词增强、用例分类法、共享提示词架构

透明的默认色键工作流、提示词增强具体规则、用例分类法（generate/edit 的完整 slug）、共享提示词 schema、生成/编辑示例、gpt-image-2 CLI 回退指南、回退 CLI 模式的临时/输出约定/依赖/环境/脚本说明，详见 `references/workflow-details.md`。

## 参考映射

- `references/prompting.md`：两种模式共享的提示词原则。
- `references/sample-prompts.md`：两种模式共享的复制粘贴提示词配方。
- `references/workflow-details.md`：透明图像工作流、提示词增强规则、用例分类法、共享提示词架构与示例、CLI 回退模型/参数/约定。
- `references/cli.md`：仅回退的 CLI 用法（`scripts/image_gen.py`）。
- `references/image-api.md`：仅回退的 API/CLI 参数参考。
- `references/codex-network.md`：仅回退的 CLI 模式网络/沙箱排障。
- `scripts/image_gen.py`：仅回退的 CLI 实现。除非用户明确选择 CLI 模式或明确确认透明请求的真正 CLI 透明回退，否则不要加载或使用。
- `$CODEX_HOME/skills/.system/imagegen/scripts/remove_chroma_key.py`：内置透明图像请求的本地后处理 helper。
