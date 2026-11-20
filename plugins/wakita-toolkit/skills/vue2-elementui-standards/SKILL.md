---
name: vue2-elementui-standards
description: >
  Vue2 + ElementUI 响应式组件与 CSS 令牌规范：断点/线性缩放、Grid 布局、
  七类卡片规格、令牌三层结构、语义视觉单一来源。
when_to_use: >
  Vue2、ElementUI、el-row、el-col、el-card、响应式卡片、卡片布局、卡片组件、Grid 布局、
  断点、breakpoint、自适应缩放、线性缩放、1280、1440、1600、1920、2560、CSS 令牌、
  design token、语义色、颜色硬编码、主题切换、Canvas 颜色。
---

# Vue2 + ElementUI 响应式组件标准化规范

> 技术栈：Vue 2 + ElementUI + CSS Grid（推荐）/ Flex 辅助  
> 与 `frontend-dashboard-layout-spec` 互补：dashboard-layout 管**页面级**骨架，本规范管**组件级**响应式

## 1. 响应式断点系统

### 1.1 断点定义

| 断点 | 宽度范围 | 推荐 Grid 列数（卡片） | 缩放基准 |
|------|---------|---------------------|---------|
| `xs` | < 1280px | 2~4 | — |
| `sm` | 1280 ~ 1439px | 2~4 | 1280px |
| `md` | 1440 ~ 1599px | 2~4 | 1440px |
| `lg` | 1600 ~ 1919px | 2~5 | 1600px |
| `xl` | 1920 ~ 2559px | 3~6 | 1920px |
| `2xl` | ≥ 2560px | 4~8 | 2560px |

### 1.2 自适应规则

- **断点之间**：卡片线性缩放（宽度、高度、字号、间距）
- **达到断点**：动态调整每行列数
- **原则**：视觉比例一致，避免挤压或过疏

---

## 2. 线性缩放实现

### 2.1 CSS 变量 + calc()

```css
:root {
  --base-width: 1280px;
  --card-base-width: 280px;
  --card-base-height: 360px;
  --font-base: 14px;
  --spacing-base: 16px;
}

@media (min-width: 1280px) {
  .card-container {
    --scale: calc(100vw / var(--base-width));   /* 核心缩放因子 */
  }
}

.card {
  width: calc(var(--card-base-width) * var(--scale));
  height: calc(var(--card-base-height) * var(--scale));
  font-size: calc(var(--font-base) * var(--scale));
  padding: calc(var(--spacing-base) * var(--scale));
}
```

### 2.2 clamp() 限制过度缩放（推荐）

```css
font-size: clamp(12px, calc(14px * var(--scale)), 18px);
padding: clamp(12px, calc(16px * var(--scale)), 24px);
```

**原则**：`clamp(最小值, 理想值, 最大值)` — 小屏不糊，大屏不炸。

---

## 3. 布局模式

### 3.1 CSS Grid（推荐）

```css
.card-grid {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  padding: 20px;
}

/* 各断点调整最小列宽 */
@media (min-width: 1440px) {
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
}
@media (min-width: 1600px) {
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
}
@media (min-width: 1920px) {
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); }
}
@media (min-width: 2560px) {
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); }
}
```

### 3.2 ElementUI 栅格（备选）

```vue
<template>
  <el-row :gutter="16" type="flex" justify="start">
    <el-col v-for="(item, i) in list" :key="i" :xs="12" :sm="8" :md="6" :lg="6" :xl="4">
      <div class="card">...</div>
    </el-col>
  </el-row>
</template>
```

| 断点 | el-col span | 每行卡片数 |
|------|-----------|----------|
| xs (<1280) | `:xs="12"` | 2 |
| sm (1280) | `:sm="8"` | 3 |
| md (1440) | `:md="6"` | 4 |
| lg (1600) | `:lg="6"` | 4 |
| xl (1920) | `:xl="4"` | 6 |

---

## 4. 卡片组件标准化

### 4.1 基础卡片骨架

```css
.card {
  width: 100%;
  max-width: 280px;           /* sm 断点基准 */
  min-width: 260px;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

/* 图片容器保持比例（16:9 示例） */
.card-img {
  width: 100%;
  padding-top: 56.25%;        /* 16:9 = 9/16 = 56.25% */
  position: relative;
  overflow: hidden;
}
.card-img img {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  object-fit: cover;
}
```

### 4.2 七类卡片规格速查表

| 卡片类型 | 图片比例 | 标题行数 | 描述/正文 | 用户信息 | 备注 |
|---------|:-------:|:------:|---------|---------|------|
| **资产卡片** | 16:9 | 1 行 | — | — | 纯展示型 |
| **专区卡片** | 16:9 | 1 行 | 2 行固定 | 用户名 1 行 + 圆形头像 | 图文混排 |
| **资讯卡片** | 16:9 左右等比 | 1 行 | ≤ 3 行 | — | 图文左右布局 |
| **课程卡片** | 16:9 | 1 行 | — | 圆形头像 | 同专区简化版 |
| **用户卡片** | 16:9 左右等比 | — | — | 圆形头像 + 名称 1 行 | 人物展示 |
| **机构卡片** | Logo 1:1 圆形 | 居中 1 行 | 4 行固定 | — | 机构展示 |
| **应用卡片** | Logo 1:1 | 1 行 | 1 行 | — | 最简卡片 |

### 4.3 ElementUI 卡片封装示例

```vue
<template>
  <el-card class="standard-card" :body-style="{ padding: '16px' }" shadow="hover">
    <!-- 图片区 -->
    <div class="card-img">
      <img :src="data.image" :alt="data.title" />
    </div>
    <!-- 内容区 -->
    <div class="card-body">
      <h3 class="card-title text-ellipsis">{{ data.title }}</h3>
      <p v-if="data.desc" class="card-desc text-clamp-2">{{ data.desc }}</p>
    </div>
    <!-- 用户区（可选） -->
    <div v-if="data.user" class="card-footer">
      <el-avatar :src="data.user.avatar" :size="24" />
      <span class="text-ellipsis">{{ data.user.name }}</span>
    </div>
  </el-card>
</template>

<style scoped>
.text-ellipsis {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.text-clamp-2 {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.text-clamp-3 {
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
}
.text-clamp-4 {
  display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
```

---

## 5. 实施要点

### 5.1 图片比例技巧

```css
/* 16:9 */  padding-top: 56.25%;
/* 4:3 */   padding-top: 75%;
/* 1:1 */   padding-top: 100%;
```

使用 `padding-top` 而非固定 `height`，保证图片容器在任意宽度下等比缩放。

### 5.2 性能

- **避免频繁 `resize` 计算**：优先用 CSS `clamp()` + `calc()` 替代 JS 监听
- **如需 JS 响应**：使用 `ResizeObserver` 或 lodash `throttle(resizeHandler, 200)`

### 5.3 测试

- Chrome DevTools → 设备模式 → 添加自定义尺寸：1280 / 1440 / 1600 / 1920 / 2560
- 每个断点验证：卡片列数、缩放比例、文字不溢出/不截断

### 5.4 间距原则

> 内容区宽度在各断点下保持固定，**两侧间距自适应变化**，而非内容无限拉伸。

```css
.page-content {
  max-width: 1200px;        /* 内容最大宽度 */
  margin: 0 auto;           /* 居中，两侧间距自动 */
  padding: 0 24px;          /* 最小安全边距 */
}
```

---

## 6. CSS 设计令牌与语义视觉统一

### 6.1 令牌三层结构

前端铺开后再改颜色，最怕色值散落。统一放一个 `tokens.css`，分三层：

1. **基础色阶**：`--brand-*` / `--accent-*` / `--ink-*`，只做调色板
2. **语义色**：`--success` / `--warning` / `--danger` / `--info`
3. **组件令牌**：如 `--viewer-bg` / `--viewer-paper` / `--viewer-paper-edge`

规则：

- 组件样式一律 `var(--token, fallback)`，禁止散落十六进制色值
- Canvas 2D / Three.js 通过 `cssToken(name, fallback)` 读同一令牌，JS 侧只读不写
- 调色只改令牌，不逐个组件改
- 令牌变更后检查不走 CSS 的渲染层（Canvas/WebGL）

### 6.2 语义视觉只有一个来源

同一种业务语义（切割/折痕/半切/齿线/忽略，或成功/警告/危险）在映射表、摘要、
列表、Canvas 预览中必须使用**同一颜色 + 同一线型**。

- 建一个 `kindStyles.ts`（或等价模块）作为唯一映射：color + dash + 中文名
- 映射表行、摘要 chip、Canvas 全部引用它；不要在各自组件里重复定义
- DXF 等原始图层色只在「上传预览」显示，并注明「原始图层色」，不混入语义色
- 中文语义名只保留一套，不混用同义词

## 审查判据（被 clean-home 的结构步骤加载时）

- 颜色、尺寸、字号、间距直接写死在组件里，未走 CSS 令牌 → E1 硬编码 P1。
- 同一业务语义在映射表、摘要、列表、Canvas 中颜色/线型不一致 → 单一来源违反 P1。
- 断点写死单一分辨率、卡片用固定高度/固定列数 → 响应式规范违反 P1。

## 检查清单

- [ ] 确认了目标断点范围（1280/1440/1600/1920/2560）
- [ ] 卡片使用 CSS Grid + `auto-fill` + `minmax`，或 ElementUI 栅格
- [ ] 字号/间距使用 `clamp()` 限制缩放范围
- [ ] 图片容器用 `padding-top` 保持比例，不用固定 height
- [ ] 文字溢出用 `text-ellipsis` 或 `-webkit-line-clamp` 截断
- [ ] 各断点下测试过卡片列数和视觉效果

## 适用边界

- 仅适用于 **Vue 2 + ElementUI**。Vue 3 + Element Plus、React、其他 UI 库的 API 与断点实现不同，不直接套用。
- 本 skill 覆盖响应式布局、卡片规格与 CSS 令牌，不覆盖业务状态管理、路由、权限等应用架构。
- 令牌方案可迁移到其他框架，但 `el-*` 组件约定与 Vue2 单文件组件语法不可直接迁移。
