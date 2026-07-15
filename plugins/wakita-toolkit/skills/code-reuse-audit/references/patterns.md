# 重复模式速查与扫描命令

> 被 SKILL.md 引用。通用识别规则 + grep 扫描模板 + 陷阱案例。

## 常见重复模式速查

| 模式 | 通用识别规则 | 抽取目标 |
|------|------------|---------|
| 时间格式化 | 同一格式化调用在多处出现（如 `strftime`/`isoformat` 配判空） | `safe_format_dt(dt, fmt)` |
| 标题/文本兜底 | `x or y[:n]` / `getattr(x, 'title', '') or ...` 各写各的 | `fallback_text(*candidates, max_len=40)` |
| 分页循环 | `while True: fetch_page(...)` 逐文件重复 | `iter_all_pages(client)` 生成器 |
| 相对时间 | 多处 `formatTime`/`timeAgo` 实现不一致 | 单一 `formatRelativeTime()` |
| 枚举映射表 | 同一组 key→label 在多处定义为对象/Map/switch | 单一 `X_LABEL_MAP` 常量，导出 `getXLabel()` |
| 徽章/标签模板 | 同一 "图标+文本" HTML/JSX 结构在多处复制 | `<XBadge>` 组件 |
| 三态视图 | `v-loading`+`el-empty`+数据视图 组合重复出现 | `<StateView>` 或 `<AsyncView>` 组件 |
| 状态标签 | 同一状态值在多处各写各的颜色/文案 | 单一 `STATUS_CONFIG` + `<StatusBadge>` |
| 列表→树转换 | 同样的 `parentId` 分组逻辑在多处出现 | `buildTree(list, parentKey)` |
| API 错误处理 | 同样的 `try/catch → toast/notification` 模式重复 | `useApi()` 或 `apiWrapper()` |

## 扫描命令模板

以下 grep 命令为通用模板——将 `Xxx`/`pattern` 替换为目标项目的实际符号后使用。

### 重复逻辑片段

```bash
# 重复的条件/兜底/格式化——替换 pattern 为实际函数名
grep -rn "pattern1\|pattern2" src/

# 重复的函数定义——替换 Xxx 为实际函数名
grep -rn "function Xxx\|const Xxx" src/ | grep -v node_modules
```

### 重复的数据定义

```bash
# 同组映射多处定义——替换 key1/key2/MapName
grep -rn "key1.*label\|key2.*color\|MapName" src/

# 常量/配置重复——替换 CONFIG_NAME
grep -rn "CONFIG_NAME\|OPTIONS\|MAP_" src/ | grep -v node_modules
```

### 重复的 UI 片段

```bash
# 相同模板结构——替换 css-class/component-name
grep -rn "css-class.*text\|component-name" src/
grep -rn "v-loading.*v-if\|el-skeleton.*el-empty" src/
```

## 陷阱案例（通用版）

1. **同名不同义**：`getLabel(key)` 在 A 模块映射的是平台名，B 模块映射的是状态名。抽取前先确认函数语义，**改名而非硬并**。
2. **兜底来源不同**：A 处用 `item.title` 兜底，B 处用 `item.summary`。抽取函数接收参数，保留调用处传不同字段。
3. **截断长度差异**：有的截 40 字有的截 80 字。共享函数用较短截断，需要更长的在调用外层补截断。
4. **同步 vs 异步**：抽取分页/请求迭代器前确认原调用是 `await` 还是同步，生成器类型要对应。
5. **CSS 重复**：全局已定义的 class，别在组件 `<style scoped>` 里再定义一份。
6. **单位/文案统一**：同一数值格式化有的用"万"有的用"w"，抽取时统一（中文项目用"万"）。
