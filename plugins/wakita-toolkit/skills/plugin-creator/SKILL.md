---
name: plugin-creator
description: 为 ZCode 创建并脚手架生成插件目录，包含必需的 `.claude-plugin/plugin.json`、可选的插件文件夹/文件、有效的 manifest 默认值，以及默认的个人 marketplace 条目。当 ZCode 需要创建新个人插件、添加可选插件结构、生成或更新 marketplace 条目以控制插件排序与可用性元数据，或在开发期间用 CLI 驱动的 cachebuster 与重装流程更新现有本地插件时使用。
---

# Plugin Creator

## 快速开始

1. 运行脚手架脚本：

```bash
# Plugin 名称被规范化为小写连字符形式，且必须 <= 64 字符。
# 默认创建在 ~/plugins/<plugin-name>。
python3 scripts/create_basic_plugin.py <plugin-name>
```

2. 编辑 `<plugin-path>/.claude-plugin/plugin.json` 填入具体元数据。脚手架以有效默认值起步，不得包含 `[TODO: ...]` 占位符。

3. 需要 marketplace 时：

```bash
python3 scripts/create_basic_plugin.py my-plugin --with-marketplace
```

默认输出到 `~/.agents/plugins/marketplace.json`（个人 marketplace，ZCode 自动发现）。仅当默认 `personal` 名称已被占用时才用 `--marketplace-name <name>`。仅当用户明确要求仓库/团队 marketplace 时才用 `--path` + `--marketplace-path`。

4. 按需生成可选伴随文件夹（`--with-skills --with-hooks --with-scripts --with-assets --with-mcp --with-apps`）。

5. 交回前验证：

```bash
python3 scripts/validate_plugin.py <plugin-path>
```

6. 开发期间更新已有本地插件——使用 cachebuster 而非重编 marketplace：

```bash
python3 scripts/update_plugin_cachebuster.py <plugin-path>
```

完整缓存刷新与重装流程见 `references/installing-and-updating.md`。

## 本 skill 创建的内容

- 在指定父目录下创建 `<plugin-name>/`，内含 `.claude-plugin/plugin.json`
- 默认个人 marketplace 条目写入 `~/.agents/plugins/marketplace.json`
- 可选：`skills/`、`hooks/`、`scripts/`、`assets/`、`.mcp.json`、`.app.json`
- 命名规则：`My Plugin` → `my-plugin`（小写连字符，连续连字符合并）

## Marketplace 规则

- 默认路径 `~/.agents/plugins/marketplace.json`（个人 marketplace），ZCode 自动发现
- 非默认路径的 marketplace 需通过 `zcode plugin marketplace add <path>` 显式安装
- 用 `scripts/read_marketplace_name.py` 读取 marketplace 名称（无参数=默认个人，带路径=指定文件）
- 生成的 `source.path` 保持 `./plugins/<plugin-name>`（相对 marketplace 根）
- 新条目默认：`policy.installation: "AVAILABLE"`、`policy.authentication: "ON_INSTALL"`、`category: "Productivity"`
- 仅当用户明确指定时才覆盖默认值或添加 `policy.products`
- 追加新条目（不重排已有顺序），除非用户要求。覆盖已有条目用 `--force`
- JSON schema 规范与完整示例见 `references/plugin-json-spec.md`

## 关键行为约束

- 外层文件夹名 = `plugin.json` 的 `"name"` = 规范化插件名，始终一致
- 不在 manifest 中留 `[TODO: ...]` 占位符
- 不写入验证会拒绝的不支持字段（如 `hooks`）
- 除非对应文件已创建，否则不把 `apps`/`mcpServers` 写入 `plugin.json`
- 保留已有 marketplace 的 `interface.displayName`
- 不要为默认个人 marketplace 告知用户运行 `zcode plugin marketplace add`——该命令仅用于非默认路径
- 更新已有插件时使用 `scripts/update_plugin_cachebuster.py` + `references/installing-and-updating.md`，不手编 marketplace 文件

## 交接 deeplink

当创建/更新了 marketplace 条目时，在最终响应中输出：
- `zcode://plugins/<规范化名称>?marketplacePath=<绝对路径>` — View 链接
- 同 URL 加 `&mode=share` — Share 链接
- 不要添加 `pluginName` 或 `hostId` 参数

## 规范参考

- `references/plugin-json-spec.md` — manifest 与 marketplace 条目的完整 JSON schema
- `references/installing-and-updating.md` — 缓存刷新、重装流程及重装后的新线程接管行为

## 验证

编辑 `SKILL.md` 后：`python3 ../skill-creator/scripts/quick_validate.py .`
交回插件前：`python3 scripts/validate_plugin.py <plugin-path>`
