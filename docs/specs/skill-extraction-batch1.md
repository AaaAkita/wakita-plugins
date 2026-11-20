# Skill 提炼第一批（项目记忆 → wakita-toolkit）

**日期**: 2026-11-19
**状态**: 开发完成
**完成日期**: 2026-11-19

## 摘要

扫描 `/home/wakita/software` 下 3 个项目的 `.agent(s)/skills`（14 个项目级 skill）与 7 个项目的 ZCode 记忆库（约 215 条记忆），把跨项目可复用的经验提炼进 wakita-toolkit：新增 5 个通用 skill，扩写 9 个现有 skill，并把项目专用的操作手册留在原项目。toolkit 版本 1.7.0 → 1.8.0（29 → 34 个 skill）。

## 背景与目标

- 项目级 `.agents/skills` 只对单个项目可见，换项目/换机器无法复用。
- 项目记忆里存在大量「一次性排障」与「可泛化工程原则」混杂；后者值得升级为插件级 skill。
- 目标：只提取跨项目可复用的原则，不搬运项目路径、容器名、服务器地址等易腐信息。

## 方案

### 新增 skill（5）

| Skill | 来源 | 核心内容 |
|-------|------|----------|
| `display-source-normalization` | YSYweb 项目 skill + 展示原则记忆 | 展示模型 + 每源适配器 + 渲染层禁来源分支；缺失=null；双源等价测试 |
| `external-integration-doc` | YSYweb `integration-plan-doc` | 对外对接文档四件事 + 三禁 + 接口签名逐条核对 |
| `canvas-interaction-space` | YSYIPP Canvas dpr / 交互容差记忆 | 屏幕空间 vs 模型空间；dpr 排查顺序；容差按像素定义 |
| `taxonomy-normalization` | YSYIAP `pattern-type-cleaning` | label→code 五步流水线；层级去重；跨类组合；未命中留原文 |
| `chinese-technical-writing` | YSYweb/YSYIPP 中文表达 feedback | spec 人话、排障汇报序号白话、错误提示中文映射、注释解释 why |

### 扩写现有 skill（9）

| Skill | 补充内容 |
|-------|----------|
| `silent-failure-audit` | 展示层/指标失真、判定层 vs 投影层、容器 healthy ≠ 调度器活着 |
| `idempotent-migration` | FULLTEXT/大表 ADD COLUMN 整表 COPY、单线程、迁移与部署时序 |
| `cd-deploy-verification` | 迁移先于服务切换、回滚半途、beat 假活、镜像源 502、多行 secret、推送纪律 |
| `config-sync-guard` | 破坏性 DB 操作人工确认、report→apply、导入后验证清单 |
| `test-quality-principles` | 管道退出码假象、格式化污染范围、本地复现生产、空分支契约 |
| `frontend-dashboard-layout-spec` | 观察窗口 > 统计报表、指标=判据计数、自检告警先证伪 |
| `playwright-cookie-injection-pitfalls` | 双 profile 目录、461 双语义、进程组信号、networkidle 不收敛 |
| `robust-architecture` | 响应模型必填字段与兜底 payload、状态判定单一事实源 |
| `vue2-elementui-standards` | CSS 令牌三层、语义视觉单一来源 |

### 不纳入 skill

- 项目专用 runbook（大屏推送、具体平台 API、服务器档案、容器端口）
- 一次性排障事实（回收站文件消失、单站点命名撞名）
- 个人偏好/占位 skill（称呼、占位模板）

## 质量加固（同日复审后）

对 34 个 skill 做结构化审计后，修复以下问题：

- `mysql-binlog-recovery`：去掉项目名、真实备份容器名与端口，改为占位符 + 示例说明；增加适用边界。
- 9 个扩写 skill 的 description 同步新增触发词：展示层失真、大表锁窗、回滚半途、破坏性 DB 操作、
  假绿、观察窗口、461/profile/networkidle、响应模型兜底、CSS 令牌。
- `docker-expert`：重复的「## 六」改为「## 七」；与 `docker-compose-prod-default` 增加分工边界。
- `compose-cd-deploy-pitfalls`：与 `cd-deploy-verification` 去重，前者只保留 compose 特有陷阱
  （迁移阻塞健康检查、heredoc 吃 stdin、FULLTEXT 大表迁移），通用验证改为交叉引用；修正失真的 description
  （原描述仍写「tag 漂移」，正文实际是 heredoc 问题）。
- `mysql-expert`：从 39 行扩展到完整专家内容（字段类型/索引/EXPLAIN/N+1/深分页/事务与锁/迁移/安全/排查命令/清单）。
- `compose-cd-deploy-pitfalls` 的实测数字标注为示例环境，不再当作通用估算。
- 为 Vue2/ElementUI、MaxScript、PyInstaller、plugin-creator、中文 commit、幂等迁移、Playwright
  增加「适用边界」，明确技术栈专用 skill 不假装通用。
- `code-reuse-audit`、`pyinstaller-packaging`、`maxscript-pitfalls`、`plugin-creator`、
  `chinese-commit-messages` 补充显式触发词。

## 技术要点 ★

### 涉及文件

- `plugins/wakita-toolkit/skills/display-source-normalization/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/external-integration-doc/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/canvas-interaction-space/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/taxonomy-normalization/SKILL.md` — 新增
- `plugins/wakita-toolkit/skills/chinese-technical-writing/SKILL.md` — 新增
- 上述 9 个现有 skill 的 SKILL.md — 追加章节
- `plugins/wakita-toolkit/.claude-plugin/plugin.json` / `kimi.plugin.json` — 1.8.0
- `.claude-plugin/marketplace.json` — 版本与 skill 计数
- `AGENTS.md` / `README.md` — skill 表与计数

### 关键约束

- 新 skill 必须只写通用原则，不出现具体项目路径、容器名、服务器地址、真实密钥
- 每个 skill frontmatter 的 `name` 必须等于目录名；description 含触发词
- 与现有 skill 重叠时优先扩写，不新建平行 skill
- 版本号按仓库规范同步 marketplace.json 的 description

## 影响范围

- toolkit 从 29 个 skill 增至 34 个；已安装用户升级后自动获得
- 不修改任何项目仓库或其 `.agents/skills`
- governance 侧仅修复 UserPromptSubmit hook 的输入健壮性，不改拦截规则

## 待确认

- [x] 5 个新 skill frontmatter 名称与目录一致
- [x] 34 个 skill 目录均含 SKILL.md，frontmatter 可被 YAML 解析
- [x] 版本号与文档计数同步
- [x] hook 在非对象 JSON / 非字符串 prompt 下仍 exit 0
- [x] 全部 skill 无项目名/容器名/真实端口泄漏
- [x] `docker-expert` 章节编号无重复
- [x] 扩写 skill 的 description 已覆盖新增章节的触发场景
