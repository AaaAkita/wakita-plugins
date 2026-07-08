---
name: chinese-commit-messages
description: |
  当用户要求提交代码、生成 commit、写 commit message、或者任何涉及 git commit 的场景时，
  必须使用这个 skill。强制要求：所有 commit message 必须用中文撰写；内容要清晰、按模块分点；
  除非用户明确说"用英文"或"写英文 commit"，否则不准在 commit message 中使用英文。
  如果用户只是随口说"提交吧"、"commit 一下"，同样适用此规则。
---

# 中文 Commit Message 规范

## 核心规则

### 1. 语言与格式

- **标题格式**：`<类型>[<scope>]: <中文描述>`
- 类型前缀必须使用英文，参考 Conventional Commits：
  - `fix:` — 修复 bug
  - `feat:` — 新增功能
  - `refactor:` — 重构（不改变外部行为）
  - `docs:` — 文档变更
  - `test:` — 测试相关
  - `chore:` — 杂项/构建/配置
  - `style:` — 代码格式（不影响逻辑，如格式化、分号等）
  - `perf:` — 性能优化
  - `ci:` — CI/CD 相关
  - `ui:` — 前端界面/视觉调整
  - `docker:` — Docker 配置变更
- **冒号后的描述必须是中文**。
- **正文描述必须是中文**。
- 技术术语（API 名、函数名、变量名、URL、文件路径）保留原样，不做翻译。
- **例外**：只有当用户明确说"用英文写 commit"、"英文 commit message"等时，才允许标题和正文都使用英文。

### 2. Scope 使用（可选但推荐）

当提交涉及特定模块时，在类型后加括号标注 scope：

| Scope | 说明 |
|-------|------|
| `(frontend)` | 前端相关（Vue、CSS、组件） |
| `(backend)` | 后端相关（Go、API、数据库） |
| `(docker)` | Docker 配置 |
| `(deps)` | 依赖更新 |
| `(ci)` | CI/CD 配置 |

示例：`feat(frontend): 新增 PageHeader 全局组件`

### 3. 标题规范

- 简洁，控制在 50 字以内。
- 使用祈使句语气（"修复"而非"修复了"）。
- 标题末尾不加句号。
- 如果涉及破坏性变更，标题前加 `BREAKING CHANGE:` 或正文开头标注。

### 4. 正文格式

```
<标题>

- <改动点1>
- <改动点2>

<注意事项/待办事项>
```

- 标题后**必须空一行**再写正文。
- 正文用 `-` 分点列出，每一点对应一个模块或一类文件。
- 按维度分组：功能改动、修复、重构、测试、配置等分开描述。
- 说明"改了什么"和"为什么改"，不要写空话。
- 如有破坏性变更、注意事项或待办事项，单独成段标注 `⚠️ 注意事项` 或 `📋 待办事项`。`

## 内容要求

### 必须包含

1. **改动的具体位置**：文件路径或模块名。
2. **改动的具体内容**：做了什么变更。
3. **改动的理由**：为什么要做这个变更（尤其重构和修复）。

### 多维度改动时的分组方式

当一次提交涉及多种性质的改动时，按以下顺序分组：

```
feat(frontend): Dashboard 重设计 + 新增 StatCard 组件

【功能】
- AdminDashboard.vue: 6 个统计指标卡片 + 快捷入口 + 系统概览双栏
- 新增 StatCard.vue 通用统计组件，支持图标/数值/标签/趋势
- StatusBadge.vue: 扩展状态映射，兼容后端大写下划线格式

【修复】
- UserImageManagement.vue: 状态标签样式回退到 neutral 的问题
- AnnotationTool.vue: 替换 el-skeleton 为 LoadingSkeleton 组件

【配置】
- style.css: 新增文化辅助色（--color-culture-500, --color-cinnabar-500）
- 新增布局工具类（.page-container, .section-card, .page-header）
```

### 注意事项区块

如有以下情况，必须在正文末尾标注：

- **破坏性变更**：`⚠️ BREAKING CHANGE: 说明影响`
- **待办事项**：`📋 TODO: 说明后续需要完成的事项`
- **依赖要求**：`🔧 依赖: 需要执行 npm install / docker-compose build`
- **回滚注意**：`⚠️ 回滚注意: 说明回滚时可能的问题`

## 示例

### 好的 commit message（功能型）

```
feat(frontend): 登录/注册页重设计为左右分栏布局

- Login.vue: 左侧品牌面板（#1a3a6e 渐变）+ 右侧表单卡片
- Register.vue: 同步登录页布局，修复 el-radio-button label→value API 弃用
- 新增 shake 动画用于表单错误提示，增加 aria-label 提升可访问性
- 使用 CSS 变量替换硬编码颜色，保持设计令牌一致性
```

### 好的 commit message（修复型）

```
fix: 任务状态提交时绕过状态机的问题

- annotation_submission_service.updateParentImageStatus 中
  任务状态更新从直接 SQL UPDATE 改为查询任务后调用
  StateMachine.TransitionTaskStatus
- 保持与母图状态转换一致，强制校验状态转换合法性
- 避免非法状态（如 RETURN_FOR_MODIFICATION）被直接覆盖为
  ANNOTATION_COMPLETED，防止母图/任务状态不一致
- 增加 StateMachine nil 保护，兼容未注入状态机的场景
- 更新相关单元测试的 SQL 期望
```

### 好的 commit message（重构型）

```
refactor(docker): 前端 Dockerfile 多阶段构建优化

- Node 版本从 18 升级到 20
- 新增非 root 用户 nginxuser 运行 nginx
- 添加 HEALTHCHECK 指令
- nginx.conf: 新增 gzip 压缩、安全响应头、静态资源长期缓存
- SPA 路由配置 try_files fallback 到 index.html

⚠️ 回滚注意: 升级 Node 版本后若构建失败，需检查 lockfile 兼容性
```

### 好的 commit message（混合型）

```
chore: 前端 UI 刷新设计系统 + 组件库 + 页面层改造

【设计系统】
- style.css: 新增三层设计令牌（primitive → semantic → component）
- 新增文化辅助色（黛色 #5B4B3A、朱砂 #C45C48）
- 新增过渡动画（fade, slide-up, shake, pulse-soft）

【全局组件】
- PageHeader.vue: 页面标题 + 副标题 + 操作按钮槽
- StatCard.vue: 统计卡片（图标 + 数值 + 标签 + 趋势）
- StatusBadge.vue: 统一状态标签（带圆点 + 柔和背景）
- EmptyState.vue: 空状态（图标 + 标题 + 描述 + 操作按钮槽）
- LoadingSkeleton.vue: 骨架屏（table/card/image/stats 模式）

【页面改造】
- AdminDashboard.vue: StatCards + 快捷入口 + 系统概览
- AdminUserManagement.vue: PageHeader + StatusBadge + LoadingSkeleton
- UserImageManagement.vue: PageHeader + StatCards + 图片网格 hover 效果
- UserUploadImageManagement.vue: StatusBadge + LoadingSkeleton + EmptyState
- AnnotationTool.vue: LoadingSkeleton 替换 el-skeleton，EmptyState 替换 el-empty

【品牌基因】
- App.vue: 导航栏底部添加 SVG 纹样装饰线

【代码质量】
- 审查修复 70+ 代码质量问题、14 项设计一致性、28 项 a11y/性能问题
- 快捷入口卡片改用 router-link 语义化标签

📋 TODO: 标注工具页三栏布局优化（P1）
```

### 差的 commit message（应避免）

```
修复：任务状态提交时绕过状态机的问题
```
（类型前缀用了中文，应该是 `fix:`）

```
fix bug in task status update
```
（描述用了英文）

```
修改了一些文件
```
（过于笼统，没有说明改了什么和为什么改）

```
feat: 优化
```
（标题太模糊，正文缺失）

## 触发场景

用户出现以下任意表述时，必须应用本规则：

- "提交"
- "commit"
- "写个 commit message"
- "生成 commit"
- "commit 一下"
- "git commit"
- "把这些改动提交"

## 执行步骤

1. **收集改动**：列出本次改动的所有文件和核心意图。
2. **确定类型和 scope**：根据改动性质选择类型前缀，如涉及特定模块添加 scope。
3. **写标题**：一句话概括总体目的，控制在 50 字以内。
4. **写正文**：
   - 按模块/维度拆分改动点，用 `-` 分点列出。
   - 多维度改动时按【功能】【修复】【重构】【配置】等分组。
   - 说明"改了什么"和"为什么改"。
5. **补充标注**：如有破坏性变更、注意事项或待办事项，在正文末尾单独成段标注。
6. **验证长度**：标题不超过 50 字，正文每行不超过 72 字。
7. **执行提交**：将 commit message 展示给用户确认，或直接用 `git commit -m "..."` 执行。
