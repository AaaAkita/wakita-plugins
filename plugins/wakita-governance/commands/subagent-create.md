---
description: 交互式生成/切换 wakita 三个用户级子智能体（scout/auditor/builder）的运行模型与思考强度
---

# /subagent-create

交互式生成或更新三个**用户级**子智能体（`wakita-scout` / `wakita-builder` / `wakita-auditor`）。自 v2.4.0 起插件不再随包分发 agent，本命令把插件内置模板渲染后写入用户级 subagent 目录 `~/.zcode/agents/`，frontmatter 含 `model:` + `thoughtLevel:` + `injectAgentsMd:`。读取本机 `~/.zcode/v2/config.json`，展示所有可用 provider 和 model 供用户选择。

- **首次运行** = 初始化生成三个子智能体文件
- **后续运行** = 切换 model / thoughtLevel（覆盖写，写前自动备份 `.bak`）

## 用法

```
/subagent-create                    # 交互式：列出可用项，引导用户选择，确认后写入
/subagent-create <provider> <model> # 直连模式：跳过选择，直接注入指定 provider+model
```

## 执行流程（交互式）

主智能体（你）按以下步骤执行，**不得跳过任何一步**：

### 1. 读取可用 provider/model

执行命令获取结构化数据：

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py" --json
```

**默认只返回可用（`enabled: true` 且 API Key 非空）的 provider**。状态为 `enabled: true` 但未填写 API Key 的 provider（如 GLM 官方、Z.ai 等内置 provider）会自动排除，避免用户选了实际无法调用的 provider。若用户明确要看全部（含不可用的），加 `--all`：

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py" --json --all
```

输出为 JSON，schema：

```json
{
  "providers": [
    {
      "key": "466f2f41-bacb-4168-b493-d0afa32a0357",
      "name": "DeepSeek",
      "enabled": true,
      "usable": true,
      "models": ["deepseek-v4-flash", "deepseek-v4-pro"]
    }
  ]
}
```

> 💡 默认过滤「可用 provider」= `enabled: true` **且** API Key 非空。直连模式（`/subagent-create <provider> <model>`）不经过此过滤，仍可注入任意 config.json 中存在的 provider。不可用 provider 可通过 `--all` 查看。

### 2. 展示给用户选择

用 `AskUserQuestion` 工具让用户选择，**不要让用户手输 provider key**（UUID 容易错）。分两步问：

**第一步：选 provider**

用 `AskUserQuestion`，把 JSON 里的 provider 列表做成选项。选项 label 用 `name`（如 "DeepSeek"），description 里标注 model 数量。例如：

- "DeepSeek" - "2 个模型（deepseek-v4-flash, deepseek-v4-pro）"
- "Bigmodel - API Key" - "2 个模型（GLM-5.2, GLM-5-Turbo）"

如果列表为空或用户想选的 provider 不在列表中，提示用户：可在 ZCode 客户端填入 API Key 并启用对应 provider 后重试，或改用直连模式 `/subagent-create <provider> <model>`。

**第二步：选 model**

根据用户选的 provider，把其 `models` 数组做成选项。例如用户选了 DeepSeek：

- "deepseek-v4-flash" - "快速版，适合日常任务"
- "deepseek-v4-pro" - "专业版，适合复杂推理"

### 3. 确认并写入

用户选定后，先跑 dry-run 让用户看到将要发生的变更：

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py" --provider <provider_key> --model <model_id>
```

输出 JSON：

```json
{
  "dry_run": true,
  "provider": "466f2f41-bacb-4168-b493-d0afa32a0357",
  "provider_name": "DeepSeek",
  "model": "deepseek-v4-flash",
  "model_value": "custom:466f2f41-bacb-4168-b493-d0afa32a0357:deepseek-v4-flash",
  "thought_level": "(template default)",
  "target_dir": "C:\\Users\\<user>\\.zcode\\agents",
  "files": [
    {"file": "wakita-scout.md", "state": "missing"},
    {"file": "wakita-builder.md", "state": "will_update"},
    {"file": "wakita-auditor.md", "state": "identical"}
  ],
  "note": "Re-run with --apply to actually write the files."
}
```

`files[].state` 含义：`missing`（将新建）/ `will_update`（将覆盖，写前备份 .bak）/ `identical`（已是目标内容，跳过）。

向用户展示 `provider_name` + `model` + `thought_level` + 各文件状态，**用 AskUserQuestion 确认是否应用**：

- "确认应用" - "将写入 ~/.zcode/agents/ 三个 agent 文件，已有文件先备份为 .bak"
- "取消" - "不做任何改动"

用户确认后，加 `--apply` 执行实际写入：

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py" --provider <provider_key> --model <model_id> --apply
```

如需覆盖思考强度（默认取模板值 `max`），追加 `--thought-level <档位>`：

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py" --provider <key> --model <id> --thought-level high --apply
```

> ⚠️ `thoughtLevel` 的合法档位由模型元数据决定（客户端不硬编码枚举），填了模型不支持的档位会在运行时报「不支持的 task 思考强度」。不确定时保持模板默认 `max`。

### 4. 提示生效方式

成功后脚本输出结构化 JSON（含 `created_files` / `updated_files` / `skipped_files`）。

**必须向用户提示**：

> ✅ 已生成/更新用户级子智能体：**DeepSeek / deepseek-v4-flash**（thoughtLevel: max）
>
> 目标目录：`~/.zcode/agents/`（已有文件已备份为 `.bak`）
>
> ⚠️ **生效方式**：ZCode 当前**无热重载**，需**关闭并重开当前会话**或**重启 ZCode 客户端**后，新会话的 Agent 工具列表才会出现/更新这三个子智能体。
>
> ⚠️ **插件升级提示**：wakita-governance 升级至 v2.4.0 后，插件级的 `wakita-governance:wakita-*` 三个 agent 自动消失，仅保留用户级版本。
>
> 如需回滚：把 `~/.zcode/agents/` 下对应 `.bak` 覆盖回 `.md` 即可。

## 直连模式

用户已在别处查过 provider/model，可直接传参跳过选择：

```bash
# 先 dry-run
python "${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py" --provider <key> --model <id>

# 确认后 apply
python "${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py" --provider <key> --model <id> --apply
```

## 错误处理

- **config.json 不存在**：提示用户先初始化 ZCode 客户端
- **provider/model 不存在**：脚本会列出所有可用项，让用户重新选
- **模板目录缺失**：提示插件安装可能损坏，重装 wakita-governance
- **权限不足**：提示用户检查 `~/.zcode/agents/` 的写权限

## 示例

```
用户: /subagent-create

[主智能体读取 --json，展示可用的 provider 列表（已启用且有 API Key）]
主智能体: 发现 2 个可用的 provider，请选择：
  - DeepSeek（2 个模型）
  - 火山引擎公司（2 个模型）

用户: DeepSeek

[主智能体展示 DeepSeek 的 2 个 model]
主智能体: 请选择模型：
  - deepseek-v4-flash（快速版）
  - deepseek-v4-pro（专业版）

用户: deepseek-v4-flash

[主智能体跑 dry-run，展示计划]
主智能体: 将把三个子智能体写入 ~/.zcode/agents/（DeepSeek / deepseek-v4-flash，thoughtLevel 取模板默认 max），确认应用？
  - 确认应用
  - 取消

用户: 确认应用

[主智能体跑 --apply]
主智能体: ✅ 已生成。需关闭并重开当前会话让子智能体生效。
```

## 实现说明

- 脚本路径：`${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py`
- `${CLAUDE_PLUGIN_ROOT}` 由 ZCode 自动展开为插件安装目录
- 模板路径：`<插件目录>/templates/agents/wakita-*.md`（脚本按自身相对路径定位，仓库态与安装态结构一致）
- 目标路径：`~/.zcode/agents/`（ZCode 用户级 subagent 根目录，自动创建）
- 脚本跨平台（Python 3.10+，macOS/Linux/Windows 通用）
- 同时支持 `config.json` 中 `provider` 为 dict / list 两种结构
- 写前自动备份为 `.bak`，幂等（内容已一致则跳过）
