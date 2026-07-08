---
name: code-reuse-audit
description: 代码复用审查与重构。当用户提到"有没有重复代码""可复用""抽取组件/工具函数""代码冗余""审查复用"或新功能开发前想统一基础设施时使用。也适用于定期消除技术债。
metadata:
  short-description: 扫描重复代码并抽取共享层
---

# 代码复用审查与重构

把散落在各文件的重复逻辑抽取到统一的共享层（工具函数 / 常量 / 组件），消除"复制粘贴"式冗余。

## 何时触发

- 用户说"有没有重复代码""可复用""抽取组件/工具函数""代码冗余"
- 新功能开发前想先统一基础设施
- 定期消除技术债
- 审查某个改动时发现"这个逻辑好像在别处也写过"

## 核心原则

1. **先扫描再动手**：用 grep/Explore agent 全局扫描重复模式，列出清单，确认后再改。
2. **纯重构不改行为**：不增删功能、不改 API 响应、不改路由。外部行为零变化。
3. **单一真源**：每个概念只有一个权威定义处（如平台映射只在 platform-config.ts，不允许多处定义）。
4. **薄包装可接受**：调用方如需空值兜底等差异，保留薄包装转发函数是合理的，不必强行消灭。
5. **逐项独立交付**：每项抽取可单独验证（build 通过 + 运行正常），不要攒到最后一起测。

## 工作流程

### 第一步：扫描重复（用 Explore agent 或 grep）

并行扫描三类重复：

**1. 重复逻辑片段**
```
# 后端：重复的条件/兜底/格式化
grep -rn "\.isoformat() if .* else" backend/app/
grep -rn "item.title or\|title.*无标题" backend/app/

# 前端：重复的函数定义
grep -rn "function formatTime\|const formatTime" frontend/src/
grep -rn "function platformLabel\|const platformLabel" frontend/src/
```

**2. 重复的数据定义**
```
# 前端：同一份映射多处定义（颜色冲突是 bug 信号）
grep -rn "weibo.*微博\|微博.*color" frontend/src/
grep -rn "platformMap\|PLATFORM_CONFIG\|platformOptions" frontend/src/
```

**3. 重复的 UI 片段**
```
# 前端：相同的模板结构
grep -rn "p-icon-mini.*plat-name\|平台.*图标" frontend/src/
grep -rn "v-loading.*el-empty\|el-skeleton.*el-empty" frontend/src/
```

### 第二步：列清单 + 定优先级

输出表格：模式 | 重复处数 | 抽取目标 | 优先级

| 优先级 | 判断标准 |
|--------|---------|
| 高 | 3+ 处重复且定义冲突（颜色/逻辑不一致，是潜在 bug） |
| 高 | 8+ 处模板片段完全相同 |
| 中 | 3-5 处重复但逻辑一致 |
| 低 | 2 处重复或语义略有差异 |

### 第三步：抽取共享层

按优先级逐项抽取，每项三步走：

**抽取到哪**：
- 后端工具函数 → `utils/` 下对应文件（text_processing.py / 时间 / 文本）
- 前端工具函数 → `utils/format.ts` 或专门的 utils 文件
- 前端常量 → 已有的 config 文件（如 platform-config.ts）
- 前端组件 → `components/common/`

**抽取模板**（函数）：
```ts
// utils/format.ts — 统一真源
export function formatRelativeTime(time: string | null | undefined): string { ... }
```
```python
# utils/text_processing.py — 统一真源
def fallback_title(title, summary) -> str: ...
```

**抽取模板**（组件）：
```vue
<!-- components/common/PlatformBadge.vue -->
<template>
  <span class="platform-badge">
    <span class="p-icon-mini" v-html="getPlatformSvg(platform)" />
    <span class="plat-name">{{ getPlatformLabel(platform) }}</span>
  </span>
</template>
<script setup lang="ts">
import { getPlatformSvg, getPlatformLabel } from '@/utils/platform-config'
defineProps<{ platform: string }>()
</script>
```

### 第四步：替换调用处

每处改为 import 共享层 + 调用，删除本地定义。

**注意保留必要的薄包装**：调用方如需空值兜底（如 `level` 可能 undefined），保留薄包装是合理的：
```ts
// ReportViewer.vue — 保留 undefined 兜底
function riskLabel(level: string | undefined) {
  return level ? getRiskLabel(level) : '未评估'
}
```

### 第五步：逐项验证

每项改完立即验证：
```bash
# 前端
npm run build  # 0 TS 错误

# 后端
docker compose restart backend && curl -s -o /dev/null -w "%{http_code}" http://localhost:6210/api/v1/health/live
# 预期 200
```

## 常见重复模式速查

| 模式 | 典型表现 | 抽取目标 |
|------|---------|---------|
| 时间格式化 | `field.isoformat() if field else None`（后端 N 处） | `safe_isoformat(dt)` |
| 标题兜底 | `item.title or item.content[:40]` 各写各的 | `fallback_title(title, summary)` |
| 分页循环 | `while True: scroll(...)` 逐行重复 | `scroll_all()` 迭代器 |
| 相对时间 | 4 处 formatTime 实现不一致 | `formatRelativeTime()` |
| 平台映射 | 3 套定义颜色冲突 | 单一 `PLATFORM_CONFIG` |
| 标签映射 | sentimentLabel/riskLabel 各重写 | `getSentimentLabel()` |
| 平台徽章 | 8 处复制"图标+名称"模板 | `<PlatformBadge>` |
| 三态视图 | v-loading+el-empty+el-skeleton | `<StateView>` |

## 陷阱与注意事项

1. **同名不同义**：`Alert.vue` 的 `getPlatformLabel` 实际映射预警类型，不是平台。统一前先确认函数语义，改名而非硬并。
2. **兜底来源不同**：dashboard 用 `item.content` 兜底，vector_service 用 `item.summary`。抽取函数接收参数，保留调用处传不同字段。
3. **截断长度差异**：有的 `[:40]` 有的 `[:80]`。共享函数内部截断到 40，需 80 的保留外层截断。
4. **同步 vs 异步**：抽取分页迭代器前确认原调用是同步还是异步（`await client.scroll` vs `client.scroll`），生成器要对应。
5. **CSS 重复**：全局已定义的样式，别在组件里局部再定义一份（如 `p-icon-mini` 在全局有，Dashboard 又写了一遍）。
6. **单位统一**：formatNumber 有的用"w"有的用"万"，抽取时统一一种（中文项目用"万"）。

## 完成验收

```bash
# 后端：无残留重复
grep -rc "\.isoformat() if .* else None" backend/app/ | grep -v ":0"  # 预期空
grep -rn "item.title or" backend/app/services/  # 预期空

# 前端：无散落定义
grep -rn "function formatTime\|const platformMap" frontend/src/ | grep -v node_modules  # 预期空
grep -rn "const platformOptions" frontend/src/  # 预期空

# 构建 + 运行
cd frontend && npm run build 2>&1 | tail -3  # 成功
docker compose restart backend && curl -s -o /dev/null -w "%{http_code}" http://localhost:6210/api/v1/health/live  # 200
```
