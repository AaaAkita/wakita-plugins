---
name: canvas-interaction-space
description: >
  Canvas/WebGL 与 DOM 叠加层错位、指针吸附/命中手感差、缩放后交互容差变化时的排查与设计规范。
  核心：屏幕空间与模型空间是两套坐标系。先验证 devicePixelRatio 与 canvas CSS 尺寸，再怀疑锚点；
  交互容差按屏幕像素定义再换算成模型单位；坐标转换只保留一个来源。
  触发词：Canvas 错位、CSS2D 标签飘移、叠加层偏移、WebGL 坐标、devicePixelRatio、dpr、
  setSize、updateStyle、吸附不灵、命中半径、点击选不中、缩放后手感、屏幕像素、模型单位、
  screen space、model space、overlay alignment。
---

# Canvas / DOM 交互空间规范

## 核心命题

**屏幕空间（像素，受 dpr 与 CSS 布局影响）与模型空间（mm/世界单位，受相机与投影影响）
是两套坐标系。** 错位和手感问题多数不是几何公式错，而是两层用了不同像素坐标系。

## 何时触发

- Canvas/WebGL 画面与 CSS2D 标签、tooltip、选择框、选框错位
- 偏移随「离画布左上角距离」线性增长（典型 dpr 症状）
- 指针吸附/命中很差，但几何算法看起来正确
- 缩放画布后点击位置/吸附手感变了
- 全屏工具页在矮视口下顶部或底部被顶出屏幕

## 一、错位排查顺序（不要先改锚点）

1. **验 dpr 尺寸一致性**：

   ```js
   canvas.width / window.devicePixelRatio === canvas.getBoundingClientRect().width
   canvas.height / window.devicePixelRatio === canvas.getBoundingClientRect().height
   ```

   不相等 → 先修尺寸同步，再谈投影/锚点。
2. **检查 `setSize` 是否传了 `updateStyle=false`**：传 false 时必须给 canvas 设 CSS
   `width/height: 100%`，否则 dpr>1 时画面被放大而 DOM 层仍按逻辑像素布局。
3. **确认容器尺寸变化被监听**：用 `ResizeObserver` 同步渲染器与相机，不用 window.resize 猜。
4. 以上都一致，才怀疑投影矩阵、锚点外推、坐标转换顺序。

## 二、交互容差：屏幕像素优先

几何容差（清洗、去重、断线闭合）与交互容差（人点不点得中）量纲不同，**禁止混用**。

- 命中/吸附半径先按屏幕像素定义，例如：顶点 10px、线段投影 8px、线段点选 8px。
- 再按当前视图比例换算成模型单位：`modelRadius = px / pixelsPerModelUnit`。
- 预览画布把 `scale` 回传给页面，缩放后手感保持一致。
- 吸附优先级固定：顶点 > 等分点（可选）> 线段投影 > 正交锁定（角度阈值 + 修饰键强制）。
- 起笔前悬停就显示吸附标记，让用户知道会吸到哪里。

## 三、坐标转换单一来源

- 页面层只调用一个 `screenToModel(event)` / `modelToScreen(point)`，不要在组件里各写一套。
- 三分量坐标（x/y/z）转换时明确哪个轴受 dpr、哪个轴受相机投影。
- 事件坐标统一从 `pointer` 事件取，不用同时混 `clientX/offsetX/pageX`。
- 任何「看起来差一点」的问题，先打印同一事件在两条链路上的坐标值对照。

## 四、全屏工具页布局

- 外壳：`height: 100vh; height: 100dvh; min-height: 0; overflow: hidden`
- 顶栏/步骤条/底栏：`flex: 0 0 auto`
- 工作区：`display: grid; grid-template-rows: minmax(0, 1fr); min-height: 0; overflow: hidden`
- 左右面板：`min-height: 0; overflow: auto`
- 预览/Canvas：去掉固定 `min-height`，改 `flex: 1; min-height: 0`，跟随容器 ResizeObserver
- 验收：`document.documentElement.scrollHeight === window.innerHeight`，底栏底边不超出视口

## 检查清单

- [ ] `canvas.width / dpr === getBoundingClientRect().width`（height 同理）
- [ ] `setSize` 的 `updateStyle` 参数与 canvas CSS 尺寸匹配
- [ ] 容器尺寸变化有 ResizeObserver 同步
- [ ] 交互容差以屏幕像素定义并随 scale 换算
- [ ] 坐标转换只有一个出入口
- [ ] 全屏页无固定 min-height 把顶/底顶出视口
- [ ] 缩放前后各点一次同一目标，命中一致

## 反模式

- ❌ 用几何容差（如 0.1mm 清洗容差）直接当吸附半径 → 13px/mm 时只有 1-2 像素
- ❌ 先改锚点外推公式解释一个屏幕空间现象
- ❌ 用 `height: 100%` 代替 flex + `min-height: 0`
- ❌ 在多个组件里各写一份 screenToModel

## 真实案例（脱敏）

3D 预览的 CSS2D 面板编号大幅飘移。最初归因标签锚点公式，只能解释几十像素；真因是
`renderer.setSize(w, h, false)` 未同步 canvas CSS 尺寸，dpr>1 时 3D 画面被放大，
而 CSS2D 标签层按逻辑像素定位，偏移随离左上角距离线性增长。修复后锚点外推作为次要
缺陷单独处理。

## 关联 skill

- `frontend-dashboard-layout-spec` — 看板布局
- `vue2-elementui-standards` — 响应式断点与 CSS 令牌
