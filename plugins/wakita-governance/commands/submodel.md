---
description: 交互式切换 wakita-governance 三个子智能体（scout/auditor/builder）的运行模型
---

# /submodel

交互式切换 wakita-governance 三个子智能体（`wakita-scout` / `wakita-builder` / `wakita-auditor`）的 `model:` 字段。读取本机 `~/.zcode/v2/config.json`，展示所有可用 provider 和 model 供用户选择，注入到插件安装目录下的 agent frontmatter，完成后提示生效方式。

## 用法

```
/submodel                    # 交互式：列出可用项，引导用户选择，确认后注入
/submodel <provider> <model> # 直连模式：跳过选择，直接注入指定 provider+model
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

	> 💡 默认过滤「可用 provider」= `enabled: true` **且** API Key 非空。部分内置 provider（GLM 官方、Z.ai 等）虽然 `enabled: true` 但未填入 API Key，用户选了也无法调用，因此默认隐藏。直连模式（`/submodel <provider> <model>`）不经过此过滤，仍可注入任意 config.json 中存在的 provider，便于高级用户切换到刚开通但尚未重启客户端的 provider。不可用 provider 可通过 `--all` 查看。

### 2. 展示给用户选择

用 `AskUserQuestion` 工具让用户选择，**不要让用户手输 provider key**（UUID 容易错）。建议分两步问：

**第一步：选 provider**

	用 `AskUserQuestion`，把 JSON 里的 provider 列表做成选项。由于第 1 步默认已过滤掉不可用项（未启用或无 API Key），这里展示的都是可用 provider，选项 label 用 `name`（如 "DeepSeek"），description 里标注 model 数量。例如：

- "DeepSeek" - "2 个模型（deepseek-v4-flash, deepseek-v4-pro）"
- "Bigmodel - API Key" - "2 个模型（GLM-5.2, GLM-5-Turbo）"
- "火山引擎公司" - "2 个模型"

	如果列表为空或用户想选的 provider 不在列表中（例如刚开通还没重启客户端，或已启用但未填 API Key），提示用户：可在 ZCode 客户端填入 API Key 并启用对应 provider 后重试，或用 `--all` 查看全部 provider，或改用直连模式 `/submodel <provider> <model>`（需用户已知 provider key）。

**第二步：选 model**

根据用户选的 provider，把其 `models` 数组做成选项。例如用户选了 DeepSeek：

- "deepseek-v4-flash" - "快速版，适合日常任务"
- "deepseek-v4-pro" - "专业版，适合复杂推理"

### 3. 确认并注入

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
  "note": "Re-run with --apply to actually write the change."
}
```

向用户展示 `provider_name` + `model` + `model_value`，**用 AskUserQuestion 确认是否应用**：

- "确认应用" - "将写入三个 agent 文件，写前自动备份为 .bak"
- "取消" - "不做任何改动"

用户确认后，加 `--apply` 执行实际写入：

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py" --provider <provider_key> --model <model_id> --apply
```

### 4. 提示生效方式

成功后脚本输出结构化 JSON：

```json
{
  "ok": true,
  "applied": true,
  "version": "2.0.4",
  "provider": "466f2f41-bacb-4168-b493-d0afa32a0357",
  "provider_name": "DeepSeek",
  "model": "deepseek-v4-flash",
  "model_value": "custom:466f2f41-bacb-4168-b493-d0afa32a0357:deepseek-v4-flash",
  "updated_files": ["wakita-scout.md", "wakita-builder.md", "wakita-auditor.md"],
  "skipped_files": [],
  "restart_hint": "ZCode 当前不支持热重载已加载的 agent。需新开会话让新 model 生效。请关闭当前会话或重启 ZCode 客户端。"
}
```

**必须向用户提示**：

> ✅ 已切换子智能体模型：**DeepSeek / deepseek-v4-flash**
>
> 已更新文件：wakita-scout.md、wakita-builder.md、wakita-auditor.md（原文件备份为 `.bak`）
>
> ⚠️ **生效方式**：ZCode 当前**无热重载/重置会话功能**（关注官方更新），新模型需**关闭并重开当前会话**或**重启 ZCode 客户端**后才会生效。当前会话内的子智能体仍按旧模型运行。
>
> 如需回滚：把对应 agent 的 `.bak` 覆盖回 `.md` 即可。

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
- **插件未安装**：提示用户先在 ZCode 客户端安装 wakita-governance 插件
- **权限不足**：提示用户检查插件安装目录的写权限

## 示例

```
用户: /submodel

[主智能体读取 --json，展示可用的 provider 列表（已启用且有 API Key）]
主智能体: 发现 2 个可用的 provider，请选择：
  - DeepSeek（2 个模型）
  - 火山引擎公司（2 个模型）
（Bigmodel - API Key 已启用但未配置 API Key，已被自动过滤）

用户: DeepSeek

[主智能体展示 DeepSeek 的 2 个 model]
主智能体: 请选择模型：
  - deepseek-v4-flash（快速版）
  - deepseek-v4-pro（专业版）

用户: deepseek-v4-flash

[主智能体跑 dry-run，展示计划]
主智能体: 将把三个子智能体切换为 DeepSeek / deepseek-v4-flash，确认应用？
  - 确认应用
  - 取消

用户: 确认应用

[主智能体跑 --apply]
主智能体: ✅ 已切换。需关闭并重开当前会话让新模型生效。
```

## 实现说明

- 脚本路径：`${CLAUDE_PLUGIN_ROOT}/scripts/inject-agent-model.py`
- `${CLAUDE_PLUGIN_ROOT}` 由 ZCode 自动展开为插件安装目录
- 脚本跨平台（Python 3.10+，macOS/Linux/Windows 通用）
- 同时支持 `config.json` 中 `provider` 为 dict / list 两种结构
- 写前自动备份为 `.bak`，幂等（已是目标值则跳过）
