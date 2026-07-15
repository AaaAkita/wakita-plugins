# Commit Message 示例库

> 被 SKILL.md 引用。完整示例供参考，核心规则见 SKILL.md。

## 好的示例

### 功能型

```
feat(frontend): 登录/注册页重设计为左右分栏布局

- Login.vue: 左侧品牌面板（#1a3a6e 渐变）+ 右侧表单卡片
- Register.vue: 同步登录页布局，修复 el-radio-button label->value API 弃用
- 新增 shake 动画用于表单错误提示，增加 aria-label 提升可访问性
- 使用 CSS 变量替换硬编码颜色，保持设计令牌一致性
```

### 修复型

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

### 重构型

```
refactor(docker): 前端 Dockerfile 多阶段构建优化

- Node 版本从 18 升级到 20
- 新增非 root 用户 nginxuser 运行 nginx
- 添加 HEALTHCHECK 指令
- nginx.conf: 新增 gzip 压缩、安全响应头、静态资源长期缓存
- SPA 路由配置 try_files fallback 到 index.html

⚠️ 回滚注意: 升级 Node 版本后若构建失败，需检查 lockfile 兼容性
```

### 混合型

```
chore: 前端 UI 刷新设计系统 + 组件库 + 页面层改造

【设计系统】
- style.css: 新增三层设计令牌（primitive -> semantic -> component）
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

## 差的示例（应避免）

### 类型前缀用了中文

```
修复：任务状态提交时绕过状态机的问题
```
↑ 应该是 `fix:`，不是"修复："

### 描述用了英文

```
fix bug in task status update
```
↑ 描述必须中文

### 过于笼统

```
修改了一些文件
```
↑ 没有说明改了什么和为什么改

### 标题太模糊

```
feat: 优化
```
↑ 标题太模糊，正文缺失
