---
name: plugin-creator
description: 为 Codex 创建并脚手架生成插件目录，包含必需的 `.codex-plugin/plugin.json`、可选的插件文件夹/文件、有效的 manifest 默认值，以及默认的个人 marketplace 条目。当 Codex 需要创建新个人插件、添加可选插件结构、生成或更新 marketplace 条目以控制插件排序与可用性元数据，或在开发期间用 CLI 驱动的 cachebuster 与重装流程更新现有本地插件时使用。
---

# Plugin Creator

## 快速开始

1. 运行脚手架脚本：

```bash
# Plugin 名称会被规范化为小写连字符形式，且必须 <= 64 字符。
# 生成的文件夹名与 plugin.json 的 name 始终一致。
# 在 skill 根目录（包含本 `SKILL.md` 的目录）下运行。
# 默认创建在 `~/plugins/<plugin-name>`。
python3 scripts/create_basic_plugin.py <plugin-name>
```

2. 当请求给出具体元数据时，编辑 `<plugin-path>/.codex-plugin/plugin.json`。
   脚手架以有效默认值起步，且不得包含 `[TODO: ...]` 占位符。

3. 当插件应出现在 Codex UI 排序中时，生成或更新个人 marketplace 条目：

```bash
# 个人 marketplace 条目默认在 `~/.agents/plugins/marketplace.json`。
python3 scripts/create_basic_plugin.py my-plugin --with-marketplace
```

仅当默认的 `personal` marketplace 名称已被占用或已安装、且需要种子化不同的新 marketplace 文件时，才指定 `--marketplace-name <name>`：

```bash
python3 scripts/create_basic_plugin.py my-plugin \
  --with-marketplace \
  --marketplace-name team-local
```

仅当用户明确要求该目的地时，才使用仓库/团队 marketplace：

```bash
python3 scripts/create_basic_plugin.py my-plugin \
  --path <repo-root>/plugins \
  --marketplace-path <repo-root>/.agents/plugins/marketplace.json \
  --with-marketplace
```

当用户指定 marketplace 路径时，在告知用户从其重装之前，确保该 marketplace 已实际安装。默认的个人 marketplace 文件 `~/.agents/plugins/marketplace.json` 会被隐式发现，但其他 marketplace 路径不会。在 Windows 上，使用用户配置目录下的等价路径。

4. 按需生成/调整可选的伴随文件夹：

```bash
python3 scripts/create_basic_plugin.py my-plugin \
  --path <parent-plugin-directory> \
  --marketplace-path <marketplace-json-path> \
  --with-skills --with-hooks --with-scripts --with-assets --with-mcp --with-apps --with-marketplace
```

`<parent-plugin-directory>` 是将创建插件文件夹 `<plugin-name>` 的目录（例如 `~/plugins`）。

5. 在交回生成的插件之前，运行：

```bash
python3 scripts/validate_plugin.py <plugin-path>
```

对于开发期间更新现有本地插件，保持脚手架流程不变，使用参考而非手编 marketplace 文件：

```bash
python3 scripts/update_plugin_cachebuster.py <plugin-path>
```

除非用户明确要求特定覆盖，否则优先使用辅助工具的默认 cachebuster。关于在现有本地插件上迭代时的预期 cachebuster 与重装流程，见 `references/installing-and-updating.md`。

## 本 skill 创建的内容

- 默认基于 marketplace 的脚手架使用位于
  `~/.agents/plugins/marketplace.json` 的个人 marketplace 文件，插件通常存储在
  `~/plugins/<plugin-name>/`。
- 在 `/<parent-plugin-directory>/<plugin-name>/` 创建插件根目录。
- 始终创建 `/<parent-plugin-directory>/<plugin-name>/.codex-plugin/plugin.json`。
- 用 ingestion 路径接受的已验证 schema 形状填充 manifest。
- 当设置 `--with-marketplace` 时创建或更新 `~/.agents/plugins/marketplace.json`。
  - 若 marketplace 文件尚不存在，在添加第一个插件条目之前种子化个人 marketplace 根。
- `<plugin-name>` 使用 skill-creator 命名规则规范化：
  - `My Plugin` -> `my-plugin`
  - `My--Plugin` -> `my-plugin`
  - 下划线、空格和标点转换为 `-`
  - 结果为小写连字符定界，连续连字符合并
- 支持可选创建：
  - `skills/`
  - `hooks/`
  - `scripts/`
  - `assets/`
  - `.mcp.json`
  - `.app.json`

## Marketplace 工作流

- 个人 marketplace 创建默认到 `~/.agents/plugins/marketplace.json`。此处
  "personal marketplace" 指文件位于该路径的 marketplace。
- 仓库/团队 marketplace 创建通过 `--path` 和 `--marketplace-path` 两者 opt-in，仅当用户明确请求时。
- `--marketplace-name` 是例外路径。仅当默认的 `personal` marketplace
  名称已被占用且需要种子化不同的新 marketplace 文件时使用。
- 不要用 `--marketplace-name` 就地重命名现有 marketplace 文件。若文件
  已存在，其顶层 `name` 必须已匹配。
- 若用户指定不同的 marketplace 路径，将该 marketplace 视为需要通过 `codex plugin marketplace add` 显式安装。
- 当需要从任何
  `marketplace.json` 文件获取 marketplace 名称时，优先使用 `scripts/read_marketplace_name.py`。无参数时读取默认个人 marketplace；带显式路径时也适用于仓库/团队 marketplace。
- 在任一位置，生成的 source 路径保持 `./plugins/<plugin-name>`。
- Marketplace 根元数据支持顶层 `name` 加可选的 `interface.displayName`。
- 将 `plugins[]` 中的插件顺序视为 Codex 中的渲染顺序。除非用户明确要求重排列表，否则追加新条目。
- `displayName` 属于 marketplace `interface` 对象内部，而非单个 `plugins[]` 条目。
- 每个生成的 marketplace 条目必须包含以下全部：
  - `policy.installation`
  - `policy.authentication`
  - `category`
- 新条目默认：
  - `policy.installation: "AVAILABLE"`
  - `policy.authentication: "ON_INSTALL"`
- 仅当用户明确指定另一个允许值时才覆盖默认。
- 允许的 `policy.installation` 值：
  - `NOT_AVAILABLE`
  - `AVAILABLE`
  - `INSTALLED_BY_DEFAULT`
- 允许的 `policy.authentication` 值：
  - `ON_INSTALL`
  - `ON_USE`
- 将 `policy.products` 视为覆盖。除非用户明确请求产品门控，否则省略。
- 生成的插件条目形状：

```json
{
  "name": "plugin-name",
  "source": {
    "source": "local",
    "path": "./plugins/plugin-name"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

- 仅当有意替换同一插件名称的现有 marketplace 条目时才使用 `--force`。
- 若目标 marketplace 文件尚不存在，创建它时带顶层 `"name"`、包含 `"displayName"` 的 `"interface"` 对象和 `plugins` 数组，然后添加新条目。

- 对于全新的 marketplace 文件，根对象应如下：

```json
{
  "name": "personal",
  "interface": {
    "displayName": "Personal"
  },
  "plugins": [
    {
      "name": "plugin-name",
      "source": {
        "source": "local",
        "path": "./plugins/plugin-name"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

## 必需行为

- 外层文件夹名和 `plugin.json` 的 `"name"` 始终是相同的规范化插件名。
- 不要移除必需结构；保持 `.codex-plugin/plugin.json` 存在。
- 不要在插件 manifest 中留 `[TODO: ...]` 占位符。
- 除非伴随文件实际已创建，否则将 `apps` 和 `mcpServers` 排除在 `plugin.json` 之外。
- 省略验证会拒绝的不支持的插件 manifest 字段，包括 `hooks`。
- 若在现有插件路径内创建文件，仅当有意覆盖时才使用 `--force`。
- 保留任何现有 marketplace `interface.displayName`。
- 生成 marketplace 条目时，始终写入 `policy.installation`、`policy.authentication` 和 `category`，即使其值为默认。
- 仅当用户明确要求该覆盖时才添加 `policy.products`。
- 保持 marketplace `source.path` 相对于所选 marketplace 根为 `./plugins/<plugin-name>`。
- 仅当创建的 marketplace 文件名称不应为
  `personal`（因该名称已被占用或在别处安装）时才使用 `--marketplace-name`。
- 若 Codex 需要批准才能写入 marketplace 文件，在继续之前请求该批准。若用户偏好自己运行写入，提供确切的脚手架命令，然后从验证或后续插件编辑继续，而非让工作流含糊不清。
- 对于开发期间更新现有本地插件，不要手编 marketplace config
  或 `marketplace.json`。使用
  `references/installing-and-updating.md` 和 `scripts/update_plugin_cachebuster.py` 中记录的更新流程。
- 不要为默认个人 marketplace 流程告知用户运行 `codex plugin marketplace add`。该命令用于显式非默认 marketplace 配置，而非标准 `~/.agents/plugins/marketplace.json` 路径。
- 若用户提供了非默认 `--marketplace-path`，在给出重装说明之前确保该 marketplace 已安装。当该显式 marketplace 尚未配置时，使用 `codex plugin marketplace add <path-to-marketplace-root>`。
- 当工作流创建或更新了基于 marketplace 的插件时，以简短的 Codex app 交接结束最终面向用户的响应。说 `To view this in the Codex app:` 并将 `View <normalized plugin name>` 和 `Share <normalized plugin name>` 写为 Markdown 链接，而非原始 URL 或代码 span。
- View deeplink 使用 `codex://plugins/<normalized plugin name>?marketplacePath=<absolute marketplace.json path>`。
- Share deeplink 使用相同 URL 加 `&mode=share`。
- 用脚手架插件的真实规范化插件名和绝对 `marketplace.json` 路径替换占位符。需要时对路径段和查询值进行 URL 编码。
- 不要向这些 deeplink 添加 `pluginName` 或 `hostId` 查询参数。Codex 在用户点击链接后推导两者。
- 未创建或更新 marketplace 条目时，不要输出 `View <normalized plugin name>` 或 `Share <normalized plugin name>` 链接。

## 精确规范示例参考

对于插件 manifest 和 marketplace 条目的确切规范示例 JSON，使用：

- `references/plugin-json-spec.md`
- `references/installing-and-updating.md` 用于在现有本地插件上迭代时的更新/重装指引，以及重装后的新线程接管行为

## 验证

编辑 `SKILL.md` 后，运行：

```bash
python3 ../skill-creator/scripts/quick_validate.py .
```

在交回生成的插件之前，运行：

```bash
python3 scripts/validate_plugin.py <plugin-path>
```
