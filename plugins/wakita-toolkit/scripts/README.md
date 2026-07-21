# wakita-toolkit MCP 配置脚本

wakita-toolkit 集成了 3 个智谱（BigModel）MCP 服务，提供联网搜索、网页读取、图像理解能力。ZCode 当前不在 MCP 配置中展开环境变量，token 需通过本目录的脚本注入。

## MCP 服务清单

| 服务名 | 类型 | 作用 | 依赖 |
|--------|------|------|------|
| `zai-web-search` | http | 联网搜索（智谱 web_search_prime） | 仅需 token |
| `zai-web-page-reading` | http | 网页内容读取（智谱 web_reader） | 仅需 token |
| `zai-visual-understanding` | stdio | 图像/视频/图表理解 | 需 `npx` + Node.js 运行时 |

调用方式：主智能体在 skill 引导下使用 `mcp__zai-web-search__*`、`mcp__zai-web-page-reading__*`、`mcp__zai-visual-understanding__*` 系列工具。

## Token 获取

1. 访问 [智谱开放平台](https://open.bigmodel.cn/) 注册并创建 API Key
2. 设置环境变量：
   - **macOS / Linux**：`export ZAI_MCP_TOKEN='<your_key>'`（持久化写入 `~/.zshrc` 或 `~/.bashrc`）
   - **Windows PowerShell**：`$env:ZAI_MCP_TOKEN = '<your_key>'`（持久化用 `setx ZAI_MCP_TOKEN '<your_key>'`，需重开终端）

## 注入脚本

### 用法

```bash
# 默认自动探测最新已安装版本
python scripts/inject-mcp-token.py

# 指定版本
python scripts/inject-mcp-token.py --version 1.2.0
```

### 脚本行为

- 读取环境变量 `ZAI_MCP_TOKEN`，缺失报错退出
- 自动定位插件安装目录：
  - macOS/Linux：`~/.zcode/cli/plugins/cache/wakita-plugins/wakita-toolkit/<version>/`
  - Windows：`%USERPROFILE%\.zcode\cli\plugins\cache\wakita-plugins\wakita-toolkit\<version>\`
- 替换 `.mcp.json` 中的 `${ZAI_MCP_TOKEN}` 占位符（4 处：1 处 stdio env、3 处 http headers 中的 Authorization）
- 用字面量 `str.replace` 替换，token 含 `/`、`&`、`\` 等特殊字符也安全
- 写前备份为 `.mcp.json.bak`
- 幂等：占位符已不存在时视为成功跳过
- 保留原文件 UTF-8 无 BOM 编码和换行风格（LF/CRLF）

### 回滚

```bash
# macOS/Linux
cp plugins/wakita-toolkit/.mcp.json.bak plugins/wakita-toolkit/.mcp.json

# Windows PowerShell
Move-Item .\plugins\wakita-toolkit\.mcp.json.bak .\plugins\wakita-toolkit\.mcp.json -Force
```

## 降级策略

token 未注入或 MCP 服务不可用时，wakita-toolkit 的所有 skill 仍可正常工作，仅失去联网检索能力。skill 文档中的「外部资料检索（可选）」章节会引导主智能体在 MCP 可用时优先联网查证，不可用时降级为凭自身能力兜底。
