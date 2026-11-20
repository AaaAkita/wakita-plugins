---
name: frontend-design-system-audit
description: >
  前端设计系统一致性审查：CSS 令牌引用未定义、UI 库默认主题未映射项目令牌（两套蓝）、
  断点散值/无大屏策略、跨 app 令牌缺失、同一业务语义多套颜色。
  当用户说“令牌不生效/边框消失”“Element Plus 没接主题”“断点太乱”“大屏没适配”
  “两套蓝色”“语义色不一致”时使用。
when_to_use: 前端设计系统审计；CSS 变量/设计令牌排查；Element Plus/Ant Design 主题桥接；响应式断点与大屏策略；多 app 令牌对齐；clean-home 的前端设计系统步骤。
---

# 前端设计系统一致性审查

判断前端颜色、主题、断点是不是一套。**重点抓“不报错但静默失效”的问题**：CSS 变量拼错、UI 库默认主题没接、断点各写各的，运行时都不报错，只会让边框消失、两个蓝并存、大屏排版失控。

## 输入

- 前端目录：`apps/*/src`、`packages/*/src` 或用户指定范围。
- 令牌文件：`tokens.css`、`theme.ts`、`tailwind.config.*`、UI 库主题配置。
- 全局样式入口：`main.ts`/`main.tsx` 里 import 的 CSS。
- 包管理结构：是否 monorepo、是否有共享 `design-tokens` 包。
- 现有守护：令牌/断点 lint、stylelint、测试文件、CI 配置。

## 一、令牌定义完整性（先查这个，最容易出 P0）

CSS 自定义属性未定义且无 fallback 时，使用它的整条声明在计算期无效——不是“颜色不对”，而是边框消失、背景透明、字体回退。

1. 收集所有 `var(--x)` 引用和 `--x:` 定义。
2. 按 app/包分别比对；跨 app 缺失也算问题。
3. 判定：
   - 未定义 + 无 fallback → **P0**（声明静默失效）。
   - 未定义 + 有 fallback → **P1**（视觉上苟住，但掩盖了缺失，且不同文件 fallback 可能不一致）。
   - 定义了但从未使用 → P2（死令牌，可清理）。
4. 排除注释、文档、测试里的示例（如 `var(--token)`），不要把示例当真实引用。
5. 检查原型/设计稿里的令牌是否与实现一致；原型有、实现没有，或色值不同，记 P1 并明确哪个是设计真源。

扫描脚本（按实际目录改）：

```python
import pathlib, re, collections

for app in ("apps/web/src", "apps/admin/src"):
    root = pathlib.Path(app)
    defs, refs = set(), collections.defaultdict(list)
    for p in root.rglob("*"):
        if p.suffix not in {".css", ".scss", ".vue", ".tsx", ".jsx", ".ts", ".js"}:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        defs.update(m.group(1) for m in re.finditer(r"(--[\w-]+)\s*:", text))
        for m in re.finditer(r"var\(\s*(--[\w-]+)\s*(,)?", text):
            refs[m.group(1)].append((str(p), bool(m.group(2))))
    for token, occ in sorted(refs.items()):
        if token in defs or token.startswith("--el-"):
            continue
        no_fb = sum(1 for _, fb in occ if not fb)
        print(token, "refs=", len(occ), "no-fallback=", no_fb,
              "files=", sorted({p for p, _ in occ}))
```

## 二、UI 库主题桥接（两套蓝的根源）

项目自定义了品牌色，但 UI 库仍用默认主题，就会出现 `el-button type="primary"` 是库默认蓝、旁边自定义按钮是品牌蓝。

- **Element Plus**：查 `--el-color-primary` 及其 `light-3/5/7/8/9`、`dark-2` 是否映射到 `--brand-*`；`--el-color-success/warning/danger/info` 是否映射到项目语义色。可用 CSS 变量覆盖，也可用 `ElConfigProvider`。
- **Ant Design**：查 `ConfigProvider theme.token.colorPrimary` 等是否使用项目令牌。
- **MUI**：查 `createTheme` 的 palette 是否来自令牌。
- 只 import 了库的默认 CSS、全仓没有任何主题覆盖 → **P1**。
- 同一个页面里库组件和自定义组件的主色/成功色/危险色肉眼可见不一致 → P1，附两个组件的位置。

## 三、断点阶梯与大屏策略

规范做法：断点收敛到一份阶梯（如 640/960/1280/1600/1920/2560），断点之间线性缩放，到达断点改列数；大屏（>1280）要有明确策略，不能只有窄屏适配。

1. 收集所有 `@media (max-width: Npx)`，列出 distinct 值和出现次数。
2. 判定：
   - 散值多、同一语义宽度不一致（900/960/980 混用）→ **P1**。
   - 没有任何 `min-width` 大屏规则，且布局用固定列宽/小字号 → **P1**（2K/4K 下文字物理尺寸过小）。
   - 窄屏直接 `display:none` 砍功能 → P2，但必须是有记录的产品决策，不能默默丢功能。
3. 检查是否把断点收进令牌或共享文档；没有 → P2，建议补一份 `responsive-breakpoints.md` 或 `--bp-*` 令牌。
4. 检查现有断点守护测试：允许集与实际值是否一致；测试红着没人管，按“守护未生效”处理（见第五节）。

```bash
grep -rhoE "@media[^{]*max-width:[[:space:]]*[0-9]+px" apps/*/src | sort | uniq -c
grep -rn "@media[^{]*min-width" apps/*/src
```

## 四、语义色单一来源与跨 app 对齐

- 同一业务语义（成功/警告/危险/选中/禁用/切割/折痕等）在映射表、chip、表格、Canvas、图表、UI 库组件里是否同一颜色/线型。
- 组件里直接写 `#fff`、`#409eff`、`rgb(...)` 而不是 `var(--surface)`/`var(--on-brand)` → P1；同一语义多处定义 → P1。
- monorepo 多 app：分别导出令牌集做差集；A 有 B 没有、或同名不同值 → P1。
- 建议把基础令牌抽到共享包/共享 CSS，各 app 只覆盖主题差异，不要在各自 `tokens.css` 维护缩水副本。

## 五、守护测试是否真的在守

令牌和断点问题会复发，通常不是没人写规则，而是守护测试没生效：

- 新增的守护测试是否**已提交**（`git status` 里不能是 `??`）。
- CI 是否真的执行（`pnpm test` / `vitest run` / `pytest` 是否包含它）。
- 当前是否为绿；红着但没人处理，等于没有。
- 测试引用的规范文档是否存在（如 `docs/design/responsive-breakpoints.md`）。
- 只创建不提交、CI 不跑、文档缺失、当前红 → **P0/P1 过程问题**，必须单独列，不能因为“有测试文件”就认为有守护。

## 输出

每条发现给：

- 检查项：令牌完整性 / 主题桥接 / 断点 / 语义色 / 跨 app / 守护
- 证据：`文件:行`、令牌名/断点值/组件名
- 失效效果：边框消失、字体回退、两个蓝、布局错位等
- 级别建议：P0/P1/P2（最终由 clean-home 汇总合成）
- 修复建议：补定义、映射主题、收敛断点、抽共享令牌、提交并跑守护

## 边界

- Vue2 + ElementUI 的断点/卡片/令牌细则 → `vue2-elementui-standards`，本 skill 只做横向一致性检查。
- Dashboard/监控页的布局与信息架构 → `frontend-dashboard-layout-spec`。
- 代码结构、重复、超长、耦合 → `code-structure-metrics` / `code-reuse-audit`。
- 本 skill 不替代视觉设计评审；它只回答“令牌/主题/断点是不是一套、有没有静默失效”。
