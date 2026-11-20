# frontend-design-system-audit：前端设计系统一致性审查补漏

**日期**: 2026-11-20
**状态**: 开发完成
**完成日期**: 2026-11-20

## 摘要

YSYIPP 的一次外部前端审计暴露了 clean-home 的盲区：它能查结构、契约、安全、测试，但没有前端设计系统这一步。结果是「CSS 令牌引用未定义」「Element Plus 默认主题没接项目令牌」「断点各写各的」「跨 app 令牌缺失」这类不报错但静默失效的问题被漏掉。本 spec 新增 `frontend-design-system-audit`，并把它接入 `clean-home` 的审查路由，同时补上「守护测试只创建不提交/不跑」这一 AI 失败模式。

## 背景与目标

- 外部审计在 YSYIPP 查出：`--ink-200/--ink-400` 引用未定义（P0）、Element Plus 默认蓝与品牌蓝并存（P1）、断点散值且无大屏策略（P1）、admin 令牌缩水/硬编码（P1）。
- 这些问题有两个共同点：运行时不一定报错；都不在 clean-home 现有 Step 5 的 `code-structure-metrics` / `code-reuse-audit` 判据里。
- 现有 `vue2-elementui-standards` 管令牌和断点，但适用边界明确写「仅 Vue 2 + ElementUI」；YSYIPP 是 Vue 3.5 + Element Plus，不能直接套。
- 目标：新增一个框架中立的设计系统审查 skill，让 clean-home 在前端模块自动路由过去；并让「守护测试未生效」成为可识别的失败模式。

## 方案

### 新增 skill（1 个）

`frontend-design-system-audit`，框架中立，覆盖六类检查：

1. **令牌定义完整性**：`var(--x)` 必须有 `--x:` 定义；无 fallback 的未定义引用 P0（整条声明失效），有 fallback P1（掩盖缺失）。
2. **UI 库主题桥接**：Element Plus / Ant Design / MUI 的默认主题是否映射到项目品牌色与语义色；未映射 P1。
3. **断点阶梯与大屏策略**：收集 `@media (max-width)` 值，散值/不在阶梯 P1；无 `min-width` 大屏策略 P1。
4. **语义色单一来源**：同一业务语义在映射表、chip、Canvas、图表、UI 组件中是否同一颜色。
5. **跨 app 令牌对齐**：monorepo 各 app 的令牌集做差集；缺失或同名不同值 P1。
6. **守护测试是否生效**：测试是否已提交、纳入 CI、当前为绿、引用的规范文档是否存在；只创建不提交/CI 不跑/当前红 → P0/P1 过程问题。

### 接入 clean-home

- 新增 Step 5b「前端设计系统」：模块含 `.vue`/`.tsx`/`.css`/`.scss` 或设计令牌时，加载 `frontend-design-system-audit`；Vue2 + ElementUI 再叠加 `vue2-elementui-standards`；Dashboard/监控页再叠加 `frontend-dashboard-layout-spec`；纯后端跳过并说明。
- Step 0 增加「记下项目已有验证命令」；Step 7 增加「汇总前先跑验证；守护测试未提交/CI 不跑/当前红记证据缺口或过程问题」。

### 补现有 skill

- `code-structure-metrics` E1 增加「令牌引用未定义」判据，并路由到 `frontend-design-system-audit`，避免两处各写一套。
- `ai-code-failure-modes` 增加 D2-8「守护测试未生效」，检测方法补「查 git status / CI 配置 / 当前测试结果 / 引用的规范文档」。
- `test-quality-principles` 审查判据增加「守护测试是否生效」，与 D2-8 互相引用。

## 技术要点 ★

### 涉及文件

- `plugins/wakita-toolkit/skills/frontend-design-system-audit/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/clean-home/SKILL.md` — 新增 Step 5b、Step 0/7 验证要求
- `plugins/wakita-toolkit/skills/code-structure-metrics/SKILL.md` — E1 增加令牌引用判据
- `plugins/wakita-toolkit/skills/ai-code-failure-modes/SKILL.md` — 新增 D2-8
- `plugins/wakita-toolkit/skills/test-quality-principles/SKILL.md` — 审查判据补守护测试
- 版本与文档：`plugin.json`、`kimi.plugin.json`、`marketplace.json`、`AGENTS.md`、`README.md`

### 关键约束

- 新 skill 只写通用设计系统判据；Vue2 细则仍归 `vue2-elementui-standards`，看板布局仍归 `frontend-dashboard-layout-spec`。
- clean-home 仍只做编排，不复制设计系统规则。
- 令牌引用扫描要排除注释/测试里的 `var(--token)` 示例。
- 判定要区分「无 fallback 的 P0」和「有 fallback 的 P1」，后者不能算通过。
- 守护测试检查必须看「已提交 + CI 执行 + 当前绿 + 文档存在」四件事，不能只看文件存在。

## 影响范围

- toolkit 38 → 39 个 skill；总 skill 数 39 → 40。
- toolkit 版本 1.9.0 → 1.10.0；governance 保持 2.8.0（本次不改 hook）。
- clean-home 的前端模块审查会多加载一个 skill；纯后端模块跳过。
- 原有 skill 只追加判据/路由，不改变既有正文与触发词。

## 待确认

- [x] 新 skill `name` 与目录名一致，description < 1024 且触发词在前 250 字符内
- [x] clean-home 引用的 `frontend-design-system-audit` 存在
- [x] `code-structure-metrics` E1、`ai-code-failure-modes` D2-8、`test-quality-principles` 审查判据已补齐
- [x] 版本号与 skill 计数在 plugin.json / kimi.plugin.json / marketplace.json / AGENTS.md / README.md 一致
- [x] 全部 skill frontmatter 严格 YAML 解析通过

## 未做

- 未修改 YSYIPP 项目代码（用户明确只补 skill）。
- 未新增 Vue3/Element Plus 专项 skill；当前用框架中立的 `frontend-design-system-audit` 覆盖，后续如需 Element Plus 细规则再单独拆。
- 未改 UserPromptSubmit hook；clean-home 的 `when_to_use` 和 hook 第 9 条已足够触发。
