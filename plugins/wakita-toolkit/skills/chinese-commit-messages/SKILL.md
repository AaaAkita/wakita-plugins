---
name: chinese-commit-messages
description: |
  当用户要求提交代码、生成 commit、写 commit message、或者任何涉及 git commit 的场景时，
  必须使用这个 skill。强制要求：所有 commit message 必须用中文撰写；内容要清晰、按模块分点；
  除非用户明确说"用英文"或"写英文 commit"，否则不准在 commit message 中使用英文。
  如果用户只是随口说"提交吧"、"commit 一下"，同样适用此规则。
  触发词：git commit、提交代码、commit message、写 commit、提交信息、中文提交。
---

# 中文 Commit Message 规范

## 核心规则

1. **标题格式**：`<类型>[<scope>]: <中文描述>`
   - 类型前缀用英文（fix、feat、refactor 等 Conventional Commits 标准类型），冒号后描述用中文
   - 技术术语（API 名、函数名、变量名、文件路径）保留原样不翻译
   - 例外：仅当用户明确要求英文 commit 时才使用全英文

2. **正文用中文**，分点列出，按模块或文件分组

3. **多维度改动分组**：当涉及多种性质改动时，按以下顺序分块：
   ```
   【功能】
   - 具体改动...
   【修复】
   - 具体修复...
   【重构】
   - 具体重构...
   【配置】
   - 具体配置...
   ```

4. **注意事项标注**（如有则放在正文末尾）：
   - `⚠️ BREAKING CHANGE: 说明影响`
   - `📋 TODO: 说明后续事项`
   - `🔧 依赖: 需要执行的操作`
   - `⚠️ 回滚注意: 说明回滚风险`

## 内容要求

- **改什么**：文件路径或模块名
- **怎么改**：具体变更内容
- **为什么**：变更理由（重构/修复时尤其重要）

## 示例参考

完整示例见 `references/examples.md`。

## 适用边界

- 只管 **commit message**。代码标识符、变量名、API 名保持英文，不因本 skill 中文化。
- 用户明确要求英文 commit 时，以用户指令为准。
- PR 描述、issue、发布说明可参考同样的「中文正文 + 英文类型前缀」风格，但不属于本 skill 的强制范围。
