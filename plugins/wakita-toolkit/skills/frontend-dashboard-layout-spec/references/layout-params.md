# 看板布局参数库

> 被 SKILL.md 引用。详细的布局参数表、720P 计算基准、形状保形策略代码示例与按组件类型速查表，核心规范见 SKILL.md。

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
- 剩余给 charts-row: ~390px -> min-height: 400px 接近临界值

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
/* 饼图/圆环 - 必须保持正圆 */
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

/* 折线图/柱状图 - 宽高比 16:9 左右 */
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
/* ✅ 正确 - 用 min-height 保底 */
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
