# Git 操作文档

## 1. Git 基础概念

Git 是一个分布式版本控制系统，用于跟踪项目中文件的变化。以下是一些基本概念：

- **仓库 (Repository)**：存储项目代码和版本历史的地方
- **提交 (Commit)**：保存对文件的更改，创建一个新的版本
- **分支 (Branch)**：从主代码线上分离出来的独立开发线
- **合并 (Merge)**：将一个分支的更改整合到另一个分支
- **远程仓库 (Remote)**：位于网络或其他位置的仓库副本
- **克隆 (Clone)**：创建远程仓库的本地副本
- **拉取 (Pull)**：从远程仓库获取最新更改并合并到本地
- **推送 (Push)**：将本地更改上传到远程仓库

## 2. 基础命令

### 2.1 初始化与配置

| 命令 | 说明 | 示例 |
|------|------|------|
| `git init` | 初始化一个新的Git仓库 | `git init` |
| `git config --global user.name "Your Name"` | 设置全局用户名 | `git config --global user.name "John Doe"` |
| `git config --global user.email "your.email@example.com"` | 设置全局邮箱 | `git config --global user.email "john@example.com"` |
| `git config --list` | 查看当前配置 | `git config --list` |

### 2.2 基本操作

| 命令 | 说明 | 示例 |
|------|------|------|
| `git add <file>` | 将文件添加到暂存区 | `git add index.html` |
| `git add .` | 将所有更改添加到暂存区 | `git add .` |
| `git commit -m "commit message"` | 提交暂存区的更改 | `git commit -m "Add login page"` |
| `git status` | 查看工作区和暂存区的状态 | `git status` |
| `git log` | 查看提交历史 | `git log` |
| `git log --oneline` | 查看简洁的提交历史 | `git log --oneline` |

### 2.3 分支操作

| 命令 | 说明 | 示例 |
|------|------|------|
| `git branch` | 查看当前分支 | `git branch` |
| `git branch <branch-name>` | 创建新分支 | `git branch feature-login` |
| `git checkout <branch-name>` | 切换到指定分支 | `git checkout feature-login` |
| `git checkout -b <branch-name>` | 创建并切换到新分支 | `git checkout -b feature-login` |
| `git merge <branch-name>` | 合并指定分支到当前分支 | `git merge feature-login` |
| `git branch -d <branch-name>` | 删除分支 | `git branch -d feature-login` |

### 2.4 远程操作

| 命令 | 说明 | 示例 |
|------|------|------|
| `git remote add <name> <url>` | 添加远程仓库 | `git remote add origin https://github.com/user/repo.git` |
| `git remote -v` | 查看远程仓库 | `git remote -v` |
| `git push <remote> <branch>` | 推送更改到远程仓库 | `git push origin main` |
| `git pull <remote> <branch>` | 从远程仓库拉取更改 | `git pull origin main` |
| `git clone <url>` | 克隆远程仓库 | `git clone https://github.com/user/repo.git` |

## 3. 操作流程

### 3.1 日常开发流程

1. **更新本地仓库**：
   ```bash
   git pull origin main
   ```

2. **创建新分支**：
   ```bash
   git checkout -b feature-branch
   ```

3. **进行开发**：修改文件，添加新功能

4. **添加更改**：
   ```bash
   git add .
   ```

5. **提交更改**：
   ```bash
   git commit -m "Add new feature"
   ```

6. **推送分支**：
   ```bash
   git push origin feature-branch
   ```

7. **创建 Pull Request**：在 GitHub/GitLab 上创建 PR

8. **合并 PR**：审核后合并到主分支

9. **删除分支**：
   ```bash
   git branch -d feature-branch
   git push origin --delete feature-branch
   ```

### 3.2 Git工作流

#### 3.2.1 Git Flow

Git Flow 是一种流行的 Git 工作流程，包含以下分支：

- **main**：主分支，用于发布稳定版本
- **develop**：开发分支，整合所有功能分支
- **feature/name**：功能分支，从 develop 分支创建
- **release/version**：发布分支，从 develop 分支创建，用于准备发布
- **hotfix/name**：紧急修复分支，从 main 分支创建

#### 3.2.2 GitHub Flow

GitHub Flow 是一种更简单的工作流程：

1. 从 main 分支创建新分支
2. 在新分支上进行开发
3. 创建 Pull Request
4. 代码审查和测试
5. 合并到 main 分支
6. 部署

### 3.3 实际使用场景

#### 3.3.1 多人协作开发

```bash
# 克隆仓库
git clone https://github.com/user/repo.git

# 创建功能分支
git checkout -b feature-new

# 开发并提交
git add .
git commit -m "feat: add new feature"

# 推送分支
git push origin feature-new

# 合并到主分支后更新本地仓库
git checkout main
git pull origin main
```

#### 3.3.2 代码审查流程

1. 创建功能分支并进行开发
2. 推送分支到远程仓库
3. 在 GitHub/GitLab 上创建 Pull Request
4. 团队成员进行代码审查
5. 根据反馈进行修改
6. 审查通过后合并到主分支
7. 删除功能分支

### 3.4 解决冲突

当合并分支或拉取更改时，可能会出现冲突。解决步骤：

1. **查看冲突文件**：
   ```bash
   git status
   ```

2. **编辑冲突文件**：手动解决冲突，保留需要的代码

3. **添加解决后的文件**：
   ```bash
   git add <conflicted-file>
   ```

4. **完成合并**：
   ```bash
   git commit
   ```

### 3.5 回滚操作

#### 回滚未提交的更改

```bash
# 放弃工作区的更改
git checkout -- <file>

# 放弃所有未提交的更改
git reset --hard
```

#### 回滚已提交的更改

```bash
# 回滚到上一个提交
git reset --hard HEAD^n

# 回滚到指定提交
git reset --hard <commit-hash>

# 撤销特定提交
git revert <commit-hash>
```

## 4. 高级操作

### 4.1 标签管理

```bash
# 创建标签
git tag v1.0.0

# 推送标签
git push origin v1.0.0

# 查看标签
git tag

# 检出标签
git checkout v1.0.0
```

### 4.2 子模块

```bash
# 添加子模块
git submodule add <url> <path>

# 克隆包含子模块的仓库
git clone --recursive <url>

# 更新子模块
git submodule update --remote
```

### 4.3 贮藏

```bash
# 贮藏当前更改
git stash

# 查看贮藏列表
git stash list

# 应用贮藏
git stash apply

# 应用并删除贮藏
git stash pop

# 贮藏并添加消息
git stash push -m "WIP: feature in progress"

# 应用特定贮藏
git stash apply stash@{1}
```

### 4.4 Git钩子

Git钩子是在特定Git事件发生时自动执行的脚本。常见的钩子包括：

#### 4.4.1 提交前钩子 (pre-commit)

用于在提交前检查代码质量：

```bash
#!/bin/sh
# 运行代码检查
npm run lint

# 运行测试
npm run test

# 如果有错误，阻止提交
if [ $? -ne 0 ]; then
  echo "提交失败：代码检查或测试未通过"
  exit 1
fi
```

#### 4.4.2 推送前钩子 (pre-push)

用于在推送到远程仓库前执行检查：

```bash
#!/bin/sh
# 运行完整测试套件
npm run test:full

if [ $? -ne 0 ]; then
  echo "推送失败：测试未通过"
  exit 1
fi
```

### 4.5 其他高级操作

#### 4.5.1 重写历史

```bash
# 交互式重写历史
git rebase -i HEAD~5

# 合并多个提交
git rebase -i HEAD~3
```

#### 4.5.2 子树合并

```bash
# 添加子树
git subtree add --prefix=subdir https://github.com/user/repo.git main

# 更新子树
git subtree pull --prefix=subdir https://github.com/user/repo.git main

# 推送子树更改
git subtree push --prefix=subdir https://github.com/user/repo.git feature-branch
```

## 5. 最佳实践

### 5.1 提交消息规范

使用清晰、简洁的提交消息，遵循以下格式：

```
<类型>: <描述>

<详细说明>（可选）
```

常见类型：
- `feat`：新功能
- `fix`：修复bug
- `docs`：文档更改
- `style`：代码风格更改
- `refactor`：代码重构
- `test`：测试更改
- `chore`：构建或依赖更改

### 5.2 分支命名规范

- `main`：主分支
- `develop`：开发分支
- `feature/<feature-name>`：功能分支
- `bugfix/<bug-name>`：bug修复分支
- `hotfix/<issue-name>`：紧急修复分支
- `release/<version>`：发布分支

### 5.3 代码审查

- 定期进行代码审查
- 使用 Pull Request 进行代码审查
- 遵循项目的代码风格指南
- 确保测试通过

### 5.4 安全注意事项

- 不要提交敏感信息（密码、API密钥等）
- 使用 `.gitignore` 文件排除不需要版本控制的文件
- 定期更新依赖项以修复安全漏洞

## 6. 常见问题与解决方案

### 6.1 忘记添加文件到提交

```bash
# 修改上次提交
git add <forgotten-file>
git commit --amend --no-edit
```

### 6.2 提交消息错误

```bash
# 修改上次提交的消息
git commit --amend -m "新的提交消息"
```

### 6.3 推送被拒绝

```bash
# 先拉取最新更改
git pull --rebase origin main
# 然后推送
git push origin main
```

### 6.4 本地分支与远程分支不同步

```bash
# 查看远程分支
git fetch origin

# 重置本地分支到远程分支
git reset --hard origin/main
```

## 7. 参考资源

- [Git 官方文档](https://git-scm.com/doc)
- [Pro Git 书籍](https://git-scm.com/book/en/v2)
- [GitHub Git 指南](https://guides.github.com/introduction/git-handbook/)
- [GitLab Git 文档](https://docs.gitlab.com/ee/git/)

---

本文档提供了 Git 的基本操作指南，随着项目的发展，可能需要根据具体情况进行调整。