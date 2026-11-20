---
name: frontend-dashboard-layout-spec
description: 【前端看板/运维页规范】看板页面布局 + 信息架构。布局：全屏填充 -> flex 比例分割 -> min-size 保底 -> overflow 滚动兜底；信息架构：观察窗口优先于统计报表、指标用判据计数、自检告警先证伪。当编写或重构 Dashboard/Monitor/Analysis/调度页时使用。触发词：看板布局、dashboard、监控页、调度页、观察窗口、统计报表、指标口径、进度分母、自检告警、全屏布局、flex 布局。
---

# Frontend Dashboard Layout Spec（前端看板布局规范）

## 核心原则

看板类页面必须按以下优先级布局：

1. **全屏填充** - 最外层容器占满父级宽高（flex: 1; min-height: 0; min-width: 0）
2. **比例分割** - 内部区块按 flex 比例分配，核心内容（图表）占大头（flex: 1），辅助内容（指标卡/筛选栏）按内容高度（flex: 0 0 auto）
3. **组件填满** - 同级卡片用 flex: 1 等分父容器空间，内部元素用 flex 居中填充
4. **最小尺寸保底** - 每个容器设 min-height/min-width，以 720P（1280×720）屏幕的内容可读性为基准计算
5. **溢出滚动** - 低于 min 边界时 overflow: auto 出现滚动条，不崩布局
6. **文字与图表固定尺寸** - 文字固定 font-size（px），不随容器等比缩放；ECharts/Canvas 图表用固定 px 尺寸 + min-size 保底；容器缩到 min 边界后 overflow: auto 出滚动条，不硬撑
7. **语义标签规范** - layout 容器用 div，内容分区用 section，整页内容区用 main

## 信息架构：观察窗口，不是统计报表

布局之前先定页面回答问题的方式。运维/调度/监测类页面的价值在**定位**，不在**汇报**。

- **展示单元默认是实体**（任务/批次/平台段/队列项），不是计数卡。
  每条实体带：属主、入队/开始/结束时刻与时长、终态与原因、重试轨迹。
- 用户看到「150 条待处理」后下一步会问「谁卡在哪、为什么」——直接把答案陈列出来。
- 全自动系统的观察窗口按四问组织：
  1. 现在在跑什么
  2. 我不在时发生了什么（24h 系统自述/交接班叙事）
  3. 哪里不对劲、会不会自愈（异常自检 + 自愈说明）
  4. 还能自动跑多久（凭据倒计时、队列水位、外部配额）

### 指标口径：判断题就直接数判据

- 指标本质是「判断题」时，用**一条带条件的 COUNT** 表达该判据，
  不要用状态/分类桶拼分母。
- 分子与分母必须取自同一判据集合，否则百分比可能超过 100%。
- 用状态桶拼分母会随进度变化：数据被领走就从桶里消失 → 进度虚高、最后一批还在跑却显示 100%。

### 自检告警先证伪

自检灯条是「某一次读数的快照」，上线前必须用真实生产数据推演：
- 稀疏基线（如权威媒体）是否会让断流规则永久亮灯 → 告警疲劳
- 空列表/读取失败是否会被渲染成「全部正常」
- 面板告警与数据库/Redis 实读不一致时，以实读为准，先证伪再行动

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

## 形状保形策略概述

flex 比例分空间时，无约束的组件会被极大拉伸变形。科学的做法是**三层分离**：

1. **父容器用 min/max 夹击** - 比例分配 + min/max 双夹击，容器不会被过分拉伸或挤压。
2. **形状敏感组件用 aspect-ratio 保形** - 适用于饼图、圆环、图片、卡片封面等有固定视觉比例的元素。
3. **内容驱动组件不设 aspect-ratio** - 表格、列表、筛选栏的高度由内容行数决定，强制设 aspect-ratio 会导致文字溢出或大量空白。

到达 max 后**停止等比缩放**，多余空间变成留白，而不是继续放大让组件失真。

完整的形状保形三层约束代码示例、按组件类型速查表、4K 下 max-size 处理方式见 `references/layout-params.md`。

## 禁止行为

- ❌ height: 100%（改用 flex: 1，父级无 explicit height 时 100% 不生效）
- ❌ 图表/文字等比缩放（设 min-size 保底，不可读时出滚动条）
- ❌ flex 子项缺 min-height: 0（无法收缩到内容尺寸以下）
- ❌ 用内容撑高度替代 flex 比例分配（内容少时空缺一大截）
- ❌ 页面容器设 overflow: hidden（子内容超出被裁剪，外层 scroll 不生效）

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
  overflow: auto;
}
.top-section    { flex: 0 0 auto; }
.charts-section { flex: 1; min-height: 400px; min-width: 680px; }
</style>
```

## 参考参数库

详细的 720P 最小尺寸计算基准（含 Dashboard 骨架参考值表与高度参考计算）、形状保形策略三层约束的完整代码示例与按组件类型速查表、4K 下 max-size 处理方式见 `references/layout-params.md`。
