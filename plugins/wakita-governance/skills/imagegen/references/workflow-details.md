# 图像生成工作流详细指南

> 被 SKILL.md 引用。包含透明图像请求完整工作流、提示词增强规则、用例分类法、共享提示词架构与示例、CLI 回退模型/参数指南、回退 CLI 模式约定。核心规则见 SKILL.md。

## 目录

- [一、透明图像请求](#一透明图像请求)
- [二、提示词增强](#二提示词增强)
- [三、用例分类法（精确 slug）](#三用例分类法精确-slug)
- [四、共享提示词架构](#四共享提示词架构)
- [五、示例](#五示例)
- [六、提示词最佳实践](#六提示词最佳实践)
- [七、gpt-image-2 CLI 回退指南](#七gpt-image-2-cli-回退指南)
- [八、回退 CLI 模式约定](#八回退-cli-模式约定)

---

## 一、透明图像请求

透明图像请求仍先用内置 `image_gen`。因内置工具不暴露真正的透明背景控制，创建一个可移除的色键源图像，再本地把键色转为 alpha。

默认流程：
1. 用内置 `image_gen` 在完全纯色的色键背景上生成请求的主体。
2. 选择不太可能出现在主体中的键色：默认 `#00ff00`，绿色主体用 `#ff00ff`，蓝色主体避免 `#0000ff`。
3. 生成后把选中源图像从 `$CODEX_HOME/generated_images/...` 移动或复制进工作区或 `tmp/imagegen/`。
4. 运行已安装的 helper 路径（不是项目相对脚本路径）：
   ```bash
   python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
     --input <source> \
     --out <final.png> \
     --auto-key border \
     --soft-matte \
     --transparent-threshold 12 \
     --opaque-threshold 220 \
     --despill
   ```
5. 验证输出有 alpha 通道、透明角、合理的主体覆盖、无明显键色 fringe。若残留细 fringe，用 `--edge-contract 1` 重试一次；仅当边缘明显锯齿且主体不反光时用 `--edge-feather 0.25`。
6. 若素材项目绑定，把最终 alpha PNG/WebP 存入项目。绝不把项目引用的透明素材只留在 `$CODEX_HOME/*` 下。

透明请求的提示词这样写：

```text
Create the requested subject on a perfectly flat solid #00ff00 chroma-key background for background removal.
The background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Keep the subject fully separated from the background with crisp edges and generous padding.
Do not use #00ff00 anywhere in the subject.
No cast shadow, no contact shadow, no reflection, no watermark, and no text unless explicitly requested.
```

不要自动用 CLI `gpt-image-1.5 --background transparent --output-format png` 替代色键。当用户要求真正/原生透明、本地移除验证失败、或请求图像复杂（头发、毛发、羽毛、烟雾、玻璃、液体、半透明材质、反光物体、柔和阴影、写实产品接地、或主体颜色与所有可行键色冲突）时，先询问用户。

用简洁确认语如：

```text
This likely needs true native transparency. The default built-in path uses a chroma-key background plus local removal, but true transparency requires the CLI fallback with gpt-image-1.5 because gpt-image-2 does not support background=transparent. It also requires OPENAI_API_KEY. Should I proceed with that CLI fallback?
```

---

## 二、提示词增强

把用户提示重组为结构化、面向生产的规范。让用户目标更清晰可执行，但不要盲目加细节。视其为提示词塑形指导，而非封闭 schema。只用有帮助的行，当能实质改善清晰度时加一条简短的额外标注行。

### 具体性策略

用用户提示的具体性决定增强程度：
- 提示已具体详细则保留具体性，只做规范化/结构化。
- 提示宽泛则可在能实质改善结果时做有品味的增强。

允许的增强：构图或取景提示、打磨级别或预期用途提示、实用布局指导、支持既定请求的合理场景具体性。

不允许的增强：请求未暗示的额外角色或对象、未暗示的品牌名/口号/调色板/叙事节拍、除非周围布局支持的任意特定位置摆放。

---

## 三、用例分类法（精确 slug）

把每个请求归入一个桶，并在提示和参考中保持 slug 一致。

Generate：
- `photorealistic-natural` - 偶遇/编辑式生活场景，真实纹理和自然光照。
- `product-mockup` - 产品/包装照、目录图、周边概念。
- `ui-mockup` - app/web 界面样机和线框图；指明所需保真度。
- `infographic-diagram` - 结构化布局和文本的图表/信息图。
- `scientific-educational` - 课堂讲解、科学图示和带必需标签与准确性约束的学习视觉。
- `ads-marketing` - 带受众、品牌定位、场景和精确标语/文案的活动概念和广告创意。
- `productivity-visual` - 幻灯片、图表、工作流和数据密集的商业视觉。
- `logo-brand` - logo/标志探索，矢量友好。
- `illustration-story` - 漫画、童书插画、叙事场景。
- `stylized-concept` - 风格驱动的概念艺术、3D/风格化渲染。
- `historical-scene` - 符合时代/世界知识的场景。

Edit：
- `text-localization` - 翻译/替换图中文字，保留布局。
- `identity-preserve` - 试穿、人在场景；锁定脸/身体/姿势。
- `precise-object-edit` - 移除/替换特定元素（含室内置换）。
- `lighting-weather` - 仅改时间/季节/氛围。
- `background-extraction` - 透明背景/干净抠图。简单不透明主体先用内置 `image_gen` 加色键移除；复杂主体询问后再用 CLI 真正透明。
- `style-transfer` - 应用参考风格同时改主体/场景。
- `compositing` - 多图插入/合并，匹配光照/透视。
- `sketch-to-render` - 绘画/线稿转写实渲染。

---

## 四、共享提示词架构

用以下标注规范作为两种顶层模式的共享提示词脚手架：

```text
Use case: <taxonomy slug>
Asset type: <where the asset will be used>
Primary request: <user's main prompt>
Input images: <Image 1: role; Image 2: role> (optional)
Scene/backdrop: <environment>
Subject: <main subject>
Style/medium: <photo/illustration/3D/etc>
Composition/framing: <wide/close/top-down; placement>
Lighting/mood: <lighting + mood>
Color palette: <palette notes>
Materials/textures: <surface details>
Text (verbatim): "<exact text>"
Constraints: <must keep/must avoid>
Avoid: <negative constraints>
```

注意：
- `Asset type` 和 `Input images` 是提示脚手架，不是专用 CLI 标志。
- `Scene/backdrop` 指视觉场景。与回退 CLI `background` 参数不同，后者控制输出透明行为。
- 仅回退的执行标注如 `Quality:`、`Input fidelity:`、遮罩、输出格式、输出路径只属于 CLI 路径。不要当作内置 `image_gen` 工具参数。

增强规则：保持简短；只加能实质改善提示的细节；编辑时显式列出不变量（`change only X; keep Y unchanged`）；若有缺失的关键细节阻塞成功则提问，否则继续。

---

## 五、示例

### 生成示例（hero 图）

```text
Use case: product-mockup
Asset type: landing page hero
Primary request: a minimal hero image of a ceramic coffee mug
Style/medium: clean product photography
Composition/framing: wide composition with usable negative space for page copy if needed
Lighting/mood: soft studio lighting
Constraints: no logos, no text, no watermark
```

### 编辑示例（不变量）

```text
Use case: precise-object-edit
Asset type: product photo background replacement
Primary request: replace only the background with a warm sunset gradient
Constraints: change only the background; keep the product and its edges unchanged; no text; no watermark
```

---

## 六、提示词最佳实践

- 提示结构：场景/背景 -> 主体 -> 细节 -> 约束。
- 包含预期用途（广告、UI 样机、信息图）以设定模式和打磨级别。
- 写实用摄影用相机/构图语言。
- 仅当用户明确要求矢量输出或非图像占位符时用 SVG/矢量替代。
- 引用精确文本并指定排版+位置。
- 难词逐字母拼写并要求逐字渲染。
- 多图输入按索引引用图像并描述如何使用。
- 编辑时每次迭代重复不变量以减少漂移。
- 用单次改动的跟进迭代。
- 提示宽泛则只加能实质帮助的额外细节。
- 提示已详细则规范化而非扩展。
- 仅 CLI 回退时，模型、`quality`、`input_fidelity`、遮罩、输出格式、输出路径指南见 `references/cli.md` 和 `references/image-api.md`。
- 透明图像用内置优先的色键工作流，除非请求复杂到需要真正 CLI 透明；切换 CLI `gpt-image-1.5` 前先询问。

两种模式共享的更多原则：`references/prompting.md`。两种模式共享的复制粘贴规范：`references/sample-prompts.md`。资产类型模板（网站素材、游戏素材、线框图、logo）汇总在 `references/sample-prompts.md`。

---

## 七、gpt-image-2 CLI 回退指南

回退 CLI 默认用 `gpt-image-2`。

- 除非请求需要真正的模型原生透明输出，新 CLI/API 工作流用 `gpt-image-2`。
- 若透明请求可能需要 CLI 回退，除非用户已明确要求 `gpt-image-1.5`、`scripts/image_gen.py` 或 CLI 回退，否则用 `gpt-image-1.5` 前先询问。说明内置色键路径是默认，但真正透明需要 `gpt-image-1.5`（因 `gpt-image-2` 不支持 `background=transparent`）。
- `gpt-image-2` 图像输入始终用高保真；不要给该模型设 `input_fidelity`。
- `gpt-image-2` 支持 `quality` 值 `low`、`medium`、`high`、`auto`。
- 用 `quality low` 做快速草稿、缩略图和快速迭代。用 `medium`、`high` 或 `auto` 做最终素材、密集文本、图表、身份敏感编辑或高分辨率输出。
- 方形图通常生成最快。快速方形草稿用 `1024x1024`。
- 若用户要 4K 风格输出，横屏用 `3840x2160`，竖屏用 `2160x3840`。
- `gpt-image-2` 尺寸可为 `auto` 或 `WIDTHxHEIGHT`，需同时满足：最大边 `<= 3840px`、两边都是 `16px` 倍数、长短比 `<= 3:1`、总像素在 `655,360` 到 `8,294,400` 之间。

常用 `gpt-image-2` 尺寸：`1024x1024` 方形、`1536x1024` 横屏、`1024x1536` 竖屏、`2048x2048` 2K 方形、`2048x1152` 2K 横屏、`3840x2160` 4K 横屏、`2160x3840` 4K 竖屏、`auto`。

---

## 八、回退 CLI 模式约定

以下约定仅适用于 CLI 回退，不描述内置 `image_gen` 输出行为。

### 临时和输出约定

- 用 `tmp/imagegen/` 存中间文件（如 JSONL 批次）；用完删除。
- 最终素材写到 `output/imagegen/` 下。
- 用 `--out` 或 `--out-dir` 控制输出路径；保持文件名稳定且具描述性。

### 依赖

本仓库优先用 `uv` 管理依赖。

必需 Python 包：

```bash
uv pip install openai
```

本地色键移除和可选降采样所需：

```bash
uv pip install pillow
```

可移植性注意：若在本仓库外使用已安装的 skill，用该环境自己的包管理器装依赖到该环境。uv 管理环境下 `uv pip install ...` 仍是首选路径。

### 环境

- 实时 API 调用必须设 `OPENAI_API_KEY`。
- 用内置 `image_gen` 工具时不要问用户要 `OPENAI_API_KEY`。
- 绝不要求用户在聊天里粘贴完整密钥。请他们本地设置并确认就绪。

密钥缺失时给用户以下步骤：
1. 在 OpenAI 平台 UI 创建 API 密钥：https://platform.openai.com/api-keys
2. 把 `OPENAI_API_KEY` 设为系统环境变量。
3. 如需可引导他们为各自 OS/shell 设置环境变量。

若本环境无法安装，告诉用户缺哪个依赖及如何装到活跃环境。

### 脚本模式说明

- CLI 命令+示例：`references/cli.md`
- API 参数快速参考：`references/image-api.md`
- CLI 模式网络批准/沙箱设置：`references/codex-network.md`
