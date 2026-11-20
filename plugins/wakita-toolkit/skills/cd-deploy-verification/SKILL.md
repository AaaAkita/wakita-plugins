---
name: cd-deploy-verification
description: >
  CD 部署后的验证与回滚诊断：确认代码真的更新、healthy ≠ deployed、
  自动回滚掩盖失败、回滚后日志已消失。
when_to_use: >
  部署验证、CD 部署、自动回滚、rollback、healthy 但没更新、版本指纹、deployed_sha、
  部署后没生效、部署卡在迁移、回滚半途、beat 不跑、镜像拉取 502、迁移先于服务切换、
  多行 secret 损坏。
---

# CD 部署验证与回滚后诊断

## 铁律：healthy ≠ deployed

带自动回滚的部署流水线里，"服务 healthy"只证明**某个版本**活着，不证明**新版本**上线了。
部署失败 → 回滚 → 服务照样 healthy，一切看起来岁月静好，但代码纹丝不动。

验证部署必须核对**版本指纹**，三者至少取一：

```bash
git rev-parse HEAD              # 服务器仓库的 HEAD 是否等于目标合并提交
cat .deployed_sha               # 若 CD 写了部署指纹文件
docker exec <db> mysql -e 'SELECT * FROM alembic_version'   # 含迁移时核对版本戳
docker images --format '{{.Repository}} {{.CreatedAt}}'     # 镜像构建时间是否为此刻
```

同时看流水线每步的真实状态（`gh run view <id>`），不要只看总结论——
回滚步骤"成功"会让整次运行显得波澜不惊。

## 回滚后的失败诊断：日志已被覆盖

回滚会重建容器，失败容器的日志随之消失，`docker logs` 只剩回滚后的干净启动日志。
此时不要盲猜，用**一次性诊断容器**复现失败，全程不碰在跑的服务：

```bash
# 1. 把目标版本代码取到旁路工作区（不动服务器仓库当前检出）
git worktree add /tmp/diag <目标SHA>

# 2. 从运行中的同类容器复制完整环境变量
docker inspect <运行中容器> --format '{{range .Config.Env}}{{println .}}{{end}}' > /tmp/diag.env

# 3. 构建诊断镜像（注意服务器可能要走镜像源 build-arg，与 compose 一致）
docker build --build-arg REGISTRY=m.daocloud.io/docker.io -t diag-test /tmp/diag/backend

# 4. 同一 network 起一次性容器，不发布端口（避免与在跑服务冲突）
docker run --rm --name diag-test --network <项目_network> --env-file /tmp/diag.env diag-test
```

关键约束：

- **不要发布端口**（不加 `-p`），诊断容器只用于看启动日志/迁移行为
- 用 `docker compose run` 替代时务必 `--no-deps` 且不带 `--service-ports`
- 诊断容器的 entrypoint 若含数据库迁移，等于对真实库执行了该迁移——
  只有确认该迁移是预期变更时才这么做，否则先在临时库里验证
- 用完清理：`git worktree remove`、`docker rmi`、删 env 文件

## 部署步骤的真实顺序与事故边界

以常见「记录上一 SHA → 迁移 → 重建容器 → 健康检查 → 失败回滚」流水线为例：

1. 记录上一版本 SHA（供回滚）
2. **alembic/迁移先跑**——此时旧服务仍在线，迁移锁窗会直接影响线上读写
3. `docker compose up -d --build` 启动新版本
4. 健康检查（如 `/health/live` 连续 3 次 200）
5. 失败自动回滚到上一 SHA

已知边界：

- **部署超时被杀不会走 rollback**，会停在「迁移已完成、新代码未启动」的半途。
  此时先确认数据库版本戳，再决定是补跑新版本还是回滚迁移。
- 回滚失败（日志出现 `Rollback completed but health check still failing`）需要人工介入：
  先恢复服务，再查根因，不要在坏状态上继续 push。
- 纯文档改动不会让 compose 重建容器（无变更），但 CI/CD 仍会跑，可以放心推。
- 大表迁移必须人工低峰执行（见 `idempotent-migration` 的锁窗章节）。

## 容器 healthy 不等于调度器活着

`docker ps` 显示 `Up (healthy)` 只证明健康检查通过，不等于定时任务在派发。
实证：beat 停摆 17 分钟（历史上有过 8.5 小时），容器全程 healthy，所有定时任务停摆。

两步都要看，缺一不可：

```bash
# ① 日志最后一行的实际时间戳（不看会漏掉停摆）
docker logs --tail 1 <beat-container> | grep -o '^\[[0-9-]* [0-9:]*'
# ② 心跳键是否在刷新（和当前时间比，应 < 60 秒）
date +%s; docker exec <redis> redis-cli get beat:heartbeat
```

判定：日志时间戳停在几分钟前，或心跳键超过 300 秒未更新 → 判停摆。
恢复：重启 beat 容器（beat 不承载业务任务，不会杀掉在跑的业务任务）。
通用原则：**判断服务是否活着，看日志最后时间戳与关键 Redis 键，别信容器状态。**

## 镜像源与凭据类部署故障

- **镜像仓库 HEAD 502**：`BuildKit load metadata … 502 Bad Gateway` 常见于镜像仓库 HEAD
  端点抽风（pull 正常）。处理：在生产服务器预热基础镜像，再重跑失败的 run，
  不必重新 push。
- **GitHub Actions 多行 secret 损坏**：把 SSH 私钥等多行 secret 用 `${{ secrets.X }}`
  内联进 `run:` 会损坏内容，报误导性的 `error in libcrypto`。正确做法：
  `env: { KEY: ${{ secrets.X }} }` + `printf '%s\n' "$KEY" > file`。
- 排查密钥问题时打印结构指纹（字节数/行数/行长分布），不要打印密钥内容。

## 推送纪律

- push 到生产主干 = 触发部署 = 对外变更，必须用户明确点头；「帮我实现」不等于「帮我推」。
- 功能没做完不推；完成 → 派独立 subagent 自查 → 再推 PR。
- 本地 commit 先确认当前分支不是主干；功能分支攒够再由用户决定合并时机。

## 凭据轮换操作顺序（变更前检查清单）

部署涉及凭据变更时，顺序错误 = 全站故障。按此清单执行：

| 凭据 | 正确顺序 | 错误后果 |
|------|----------|----------|
| MySQL 密码 | 先 `ALTER USER ... IDENTIFIED BY` 改库内密码 → 再改 .env/compose → 重建容器 | 顺序颠倒：配置已变库未变，全站连接失败 |
| ENCRYPTION_KEY | 先跑"旧 key 解密 → 新 key 重加密"迁移脚本，或安排各平台数据重导入 | 直接换 key：全部 AES 加密数据无法解密 |
| JWT_SECRET | 直接换，无需前置操作 | 全部在线用户掉线重登（预期行为，选低峰期） |

另注意：MySQL 容器密码属"首次初始化数据卷才生效"，改 .env 不会改变已有数据卷里的
真实密码——这就是为什么必须先 ALTER USER。
