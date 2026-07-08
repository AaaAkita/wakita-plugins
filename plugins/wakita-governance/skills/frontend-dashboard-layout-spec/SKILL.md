---
name: frontend-dashboard-layout-spec
description: 【前端看板类界面布局规范】看板页面全屏填充 → flex比例分割 → min-size保底 → overflow滚动兜底的布局规范。当需要编写或重构 Dashboard/Monitor/Analysis 等看板类页面的 CSS 骨架布局时使用。包含三层策略：骨架flex比例、同级卡片等分、溢出兜底。
---

# Frontend Dashboard Layout Spec（前端看板布局规范）

## 核心原则

看板类页面必须按以下优先级布局：

1. **全屏填充** — 最外层容器占满父级宽高（flex: 1; min-height: 0; min-width: 0）
2. **比例分割** — 内部区块按 flex 比例分配，核心内容（图表）占大头（flex: 1），辅助内容（指标卡/筛选栏）按内容高度（flex: 0 0 auto）
3. **组件填满** — 同级卡片用 flex: 1 等分父容器空间，内部元素用 flex 居中填充
4. **最小尺寸保底** — 每个容器设 min-height/min-width，以 720P（1280×720）屏幕的内容可读性为基准计算
5. **溢出滚动** — 低于 min 边界时 overflow: auto 出现滚动条，不崩布局

## 三层策略

### 第一层：骨架 flex 比例

```
┌──────────────────────────────────────────┐
│ top-section（flex: 0 0 auto，内容高度）    │
├──────────────────────────────────────────┤
│                                          │
│ charts-section（flex: 1，撑满剩余）        │
│  min-height: 400px                       │
│  min-width: 680px                        │
│                                          │
└──────────────────────────────────────────┘
```

```css
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
  min-width: 0;
}
.top-section    { flex: 0 0 auto; }
.charts-section { flex: 1; min-height: 400px; min-width: 680px; }
```

若顶部有跑马灯/实时播报，也设为 flex: 0 0 auto 放在 top-section 和 charts-section 之间。

### 第二层：同级卡片等分

侧边栏内多张卡片用 flex: 1 等分高度：

```css
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  min-width: 320px;
}
.side-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 16px;
}
```

卡片内部横排布局（饼图左 + 图例/数值右）：

```css
.card-body {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.chart-area {
  flex-shrink: 0;
  min-height: 100px;
  min-width: 100px;
}
.legend-area {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}
```

### 第三层：溢出兜底

内容区同时处理水平和垂直溢出。注意页面容器不要设 `overflow: hidden`，否则子内容超出时被裁剪而非冒泡到外层滚动容器：

```css
.content-wrapper {
  flex: 1;
  overflow: auto;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}
```

## 组件复用原则

新增组件前必须执行以下检查：

1. **查重** — 在 `components/common/` 下搜索是否已有功能相近的组件
2. **评估通用性** — 如果该组件可能在两个或以上页面中使用，必须放在 `common/` 目录下，不得写在页面内联代码中
3. **优先泛化** — 如果已有组件功能接近但缺部分功能，优先给已有组件加 prop/slot 扩展，而非新建组件
4. **目录归属** — 单页专用组件放在 `components/<页面名>/`，跨页通用组件放在 `components/common/`

示例：情感分布饼图已在 Dashboard 和 Analysis 两个页面使用，应提取为 `common/SentimentChart.vue`。

## 720P 最小尺寸计算基准

所有 min-width/min-height 以 1280×720 屏幕为基准，确保内容可读：

### Dashboard 骨架参考值

| 容器 | min-height | min-width | 计算依据 |
|------|-----------|-----------|---------|
| charts-row | 400px | 720px | 左列 400 + 右列 300 + gap 20 |
| chart-main（走势图） | 0 | 400px | 走势图 ECharts 可读宽度 |
| charts-side（右侧面板） | 0 | 300px | 卡片内 130px 饼图 + 图例 |
| TrendChart chart-wrap | 300px | 350px | 三系列折线图最低高度 |
| 饼图 div | 90px | 90px | 饼图最低可辨尺寸 |

720P 下侧边栏折叠（64px）可用宽度 = 1280 - 64 - 48 = 1168px，满足所有 min-width 总和。

### 高度参考

720P 可用高度 ≈ 660px（扣除浏览器栏），Dashboard 消耗：
- content-wrapper padding: 32px
- stat-row: ~150px
- marquee: ~40px
- gaps: 48px
- 剩余给 charts-row: ~390px → min-height: 400px 接近临界值

## 形状保形策略（aspect-ratio + min/max 三层约束）

flex 比例分空间时，无约束的组件会被极大拉伸变形。科学的做法是**三层分离**：

### 第一层：父容器用 min/max 夹击

```css
.side-panel {
  flex: 1;
  min-width: 280px;  /* 720P 最小可读宽度 */
  max-width: 480px;   /* 4K 最大合理宽度，超出则留白 */
  display: flex;
  flex-direction: column;
}
```

比例分配 + min/max 双夹击，容器不会被过分拉伸或挤压。

### 第二层：形状敏感组件用 aspect-ratio 保形

适用于饼图、圆环、图片、卡片封面等有固定视觉比例的元素。

```css
/* 饼图/圆环 — 必须保持正圆 */
.chart-figure {
  flex: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}
.chart-area {
  width: 100%;
  max-width: 140px;     /* 4K 不超 140px */
  min-width: 90px;      /* 720P 不低 90px */
  aspect-ratio: 1;      /* 强制 1:1，永远是正圆 */
}

/* 折线图/柱状图 — 宽高比 16:9 左右 */
.line-chart-area {
  flex: 1;
  min-height: 200px;    /* 720P 最低高度 */
  max-height: 500px;     /* 4K 最高高度 */
  min-width: 300px;
  aspect-ratio: 16 / 9;
}
```

### 第三层：内容驱动组件不设 aspect-ratio

表格、列表、筛选栏的高度由**内容行数**决定，不是比例。强制设 aspect-ratio 会导致文字溢出或大量空白。

```css
/* ✅ 正确 — 用 min-height 保底 */
.data-table-wrap {
  flex: 1;
  min-height: 200px;    /* 保证至少显示几行 */
  /* 没有 aspect-ratio，没有 max-height */
}

/* ✅ 文字块用截断防止溢出 */
.text-block {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
```

### 按组件类型速查

**形状驱动组件**（必须设 aspect-ratio）：

| 组件类型 | aspect-ratio | 720P min | 4K max | overflow |
|---------|-------------|----------|--------|----------|
| 饼图/圆环卡片 | 1:1 | 90×90 | 250×250 | hidden |
| 折线图卡片 | 16:9 | 200×113 | 600×338 | hidden |
| 柱状图卡片 | 16:9 | 120×68 | 500×281 | hidden |
| 词云卡片 | 16:9 | 120×68 | 500×281 | hidden |
| 图片/封面 | 原始比例 | 按内容 | 按内容 | hidden + object-fit |

**内容驱动组件**（不设 aspect-ratio，高度由内容决定）：

| 组件类型 | 保底策略 | 说明 |
|---------|---------|------|
| 统计指标卡 | `min-height` + padding | 文字固定 font-size 不缩放 |
| 筛选栏 | 内容自然高度 | 输入框/按钮高度固定 |
| 表格 | `min-height` 保底 | 行数决定高度 |
| 文字列表 | `min-height` 保底 | 行高固定 |

> 内容驱动组件强行设置 aspect-ratio 会导致文字和内容比例失调，产生大量无意义的留白或内容溢出被裁剪。文字固定 font-size 不随容器缩放，这些组件的尺寸应由内容决定，flex 比例只分配宽度，高度自然跟随内容。

### 4K 下 max-size 的处理方式

到达 max 后**停止等比缩放**，多余空间变成留白，而不是继续放大让组件失真：

```css
.pie-chart {
  flex: 1;
  display: flex;
  justify-content: center;  /* 4K 下居中，两侧留白 */
  align-items: center;
}
.chart-area {
  max-width: 200px;
  max-height: 200px;
  aspect-ratio: 1;
}
```

## 文字与图表缩放策略

- 文字固定 font-size（px），不随容器等比缩放
- ECharts/Canvas 图表用固定 px 尺寸 + min-size 保底
- 容器缩到 min 边界后 overflow: auto 出滚动条，不硬撑

## 语义标签规范

- layout 容器用 div
- 内容分区用 section
- 整页内容区可用 main

## 禁止行为

- ❌ height: 100%（改用 flex: 1，父级无 explicit height 时 100% 不生效）
- ❌ 图表/文字等比缩放（设 min-size 保底，不可读时出滚动条）
- ❌ flex 子项缺 min-height: 0（无法收缩到内容尺寸以下）
- ❌ 用内容撑高度替代 flex 比例分配（内容少时空缺一大截）
- ❌ 页面容器设 overflow: hidden（子内容超出被裁剪，外层 scroll 不生效）
- ❌ 重复造组件（写之前先查 common/ 下有没有相近的，有就复用/扩展）

## 推荐模板

```vue
<template>
  <div class="page-container">
    <section class="top-section"><!-- 指标卡/筛选栏 --></section>
    <section class="charts-section"><!-- 图表区 --></section>
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}
.top-section    { flex: 0 0 auto; }
.charts-section { flex: 1; min-height: 400px; min-width: 680px; }
</style>
```
