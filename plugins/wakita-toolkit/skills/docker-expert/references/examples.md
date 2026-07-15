# Docker 示例库

> 被 SKILL.md 引用。完整示例供参考，核心规则见 SKILL.md。Dockerfile/Nginx/Compose 通用模板见 deployment-guide.md。

## 一、跨项目 cache mount 共用

给相同 `id` 即可让多个项目复用同一份官方依赖缓存：

```dockerfile
# 项目 A 和项目 B 的 Dockerfile 都用同一个 id
RUN --mount=type=cache,id=shared-pip,target=/root/.cache/pip \
    pip install -r requirements.txt
```

> 注意：pip/apt 是按"包名+版本"去重存储的，不同项目的依赖同名同版本会复用同一份缓存，冲突极小。但若两个项目 Python 版本不同，wheel 不通用，需按版本分 `id`（如 `id=shared-pip-py311`）。

---

## 二、前端 dev 模式改造（完整指南）

后端天然适合挂载（`python main.py` 直接跑源码），前端则不同--构建式前端是 `vite build` -> 静态文件烤进 nginx。要把前端也改成挂载开发，有六个必做的坑点。

### 2.1 用 `docker-compose.override.yml` 而非改原 compose

override 文件与 `docker-compose.yml` 同目录同名会被 `docker compose up` 自动合并，生产能力完整保留：

```bash
docker compose up                                       # 开发：自动加载 override
docker compose -f docker-compose.yml up --no-override   # 生产：不加载 override
```

### 2.2 端口冲突用 `!override` 整体替换

compose 对 list 是"追加去重"，override 里写 `6211:5173` 不会替换原 `6211:80`，会两条并存导致同宿主端口冲突。用 `!override` 标签整体替换（需 compose v2.24+）：

```yaml
services:
  frontend:
    ports: !override
      - "6211:5173"   # dev server 5173 替换原 nginx 80
```

`!reset` 是清空（不留新值），`!override` 是替换（带新值），这里要 `!override`。

### 2.3 node_modules 必须用匿名卷隔离

挂载 `./frontend:/app` 会把宿主机（Windows）的 `node_modules` 覆盖镜像内（Linux）装的，而 Windows 装的 esbuild/rollup 二进制在 Linux 容器跑不起来。用匿名卷隔离：

```yaml
volumes:
  - ./frontend:/app
  - /app/node_modules   # 匿名卷保护镜像内装的依赖，宿主机的进不来
```

匿名卷首次挂载时会从镜像对应路径拷贝内容，故镜像内 `npm install` 装的依赖会被保留。

### 2.4 dev server 的 API 代理目标必须改服务名（高频坑）

vite.config 里 `proxy.target: 'http://localhost:8000'` 在容器内指向 dev server 自己，会 502。改成读环境变量，dev 容器内设为 `backend:8000`（服务名）：

```ts
// vite.config.ts
proxy: {
  '/api': {
    target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
    // ...
  }
}
// 同时设 server.host: '0.0.0.0'，否则容器外访问不到
```

```yaml
# docker-compose.override.yml
environment:
  VITE_BACKEND_URL: http://backend:8000
```

### 2.5 dev 模式对 Node 版本比生产构建更敏感（非显然坑）

生产 Dockerfile 用 `node:18-alpine` 跑 `vite build` 可能一直正常，但改成 dev 模式跑 `npm run dev` 时会报 `The "paths[0]" argument must be of type string. Received undefined`（出在 unplugin-vue-components 加载阶段）。

根因：新版 `unplugin-vue-components@32` / `unplugin-auto-import@21` 需要 Node 20+，但生产构建路径对 node 版本容忍度高没暴露问题，dev server 加载插件时才触发。

**对策**：dev 用 `node:20-alpine`（与生产 Dockerfile 的 node 版本解耦，dev 可更高）。这也符合"Node 18 已停止维护，20 是当前 LTS"的规范。

### 2.6 完整 override 模板

```yaml
# docker-compose.override.yml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev      # node 镜像 + cache mount 装依赖 + npm run dev
    ports: !override
      - "6211:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules             # 隔离，保护镜像内依赖
    environment:
      VITE_BACKEND_URL: http://backend:8000
    depends_on:
      backend:
        condition: service_started    # 不用等 healthy，dev server 独立工作
```

---

## 三、确认 docker-mcp 是否可用

```bash
docker mcp tools list       # 列出可用工具（含 docker cli 工具）
docker mcp --version
```

---

## 四、Dockerfile.dev 模板

```dockerfile
ARG REGISTRY=docker.io
FROM ${REGISTRY}/library/node:20-slim  # ⚠️ slim(glibc) 不用 alpine(musl)

WORKDIR /app
RUN npm config set registry https://registry.npmmirror.com  # 国内源

COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install --prefer-offline --no-audit

EXPOSE 5173
CMD ["npm", "run", "dev"]
```

关键点：
- `node:20-slim` 而非 alpine——esbuild 无 musl 专用二进制，glibc 在容器内更稳定
- `--mount=type=cache` 持久化 npm 包，重复构建不重下
- 不用 `COPY . .`——源码通过 compose volumes 挂载，改代码 HMR 即时生效

---

## 五、前端 dev 模式三大坑详解

### 坑 1：esbuild `The service was stopped`

**症状**：Vite 启动 ready 但日志报 esbuild 崩溃，页面 504。

**根因**：esbuild 长驻服务（socket 通信）在 Docker 容器内不稳定，尤其旧版本。

**根治（缺一不可）**：
1. dev 镜像用 `node:20-slim`（glibc），**不用 `node:20-alpine`**（musl）。esbuild glibc 二进制在 musl 上更不稳
2. 升级 esbuild 到 0.25+（package.json 显式声明，覆盖 vite 传递的旧版 0.21.x）：
   ```bash
   npm install esbuild@latest --save
   ```
3. compose 加 `shm_size: "1gb"`（默认 64MB 偏小）

### 坑 2：`504 Outdated Optimize Dep`

**症状**：浏览器加载页面时大量 504，动态 import 的模块加载失败，Vue Router 启动报错。

**根因**：按需引组件样式（如 `element-plus/es/components/<x>/style/css`）在运行时被动态发现，Vite 触发二次预构建 → esbuild 崩 → 504。`optimizeDeps.include` 无法完整覆盖（v-loading 指令、ElMessage 等 service 组件的样式总会遗漏）。

**根治**：组件 JS 按需，样式全量引入一次：
```ts
// vite.config.ts — 关闭按需样式
AutoImport({ resolvers: [ElementPlusResolver({ importStyle: false })] })
Components({ resolvers: [ElementPlusResolver({ importStyle: false })] })

// optimizeDeps.include 只放 JS 模块（CSS 不能放，会报 Cannot optimize）
optimizeDeps: { include: ['element-plus', 'element-plus/es', '@element-plus/icons-vue'] }
```
```ts
// main.ts — 全量引一份样式
import 'element-plus/dist/index.css'
```
组件 JS 仍按需（省 JS 体积），样式不再触发二次预构建。

### 坑 3：组件命名冲突

**症状**：`[unplugin-vue-components] component "X" has naming conflicts, ignored`。

**根因**：不同目录下同名 `.vue` 文件，自动注册时冲突。

**根治**：重命名其中一个（文件名 + 引用处），别用别名绕（治标不治本）。

---

## 六、排错速查表

| 症状 | 根因 | 修复 |
|------|------|------|
| `The service was stopped` | esbuild 长驻服务在容器内崩 | slim 镜像 + esbuild 升级 + `shm_size` |
| `504 Outdated Optimize Dep` | 按需样式触发二次预构建 | 样式全量引入，`importStyle:false` |
| `Cannot optimize dependency: xxx.css` | CSS 放进了 optimizeDeps.include | include 只放 JS，CSS 用 import |
| 页面白屏、容器外访问不到 | dev server 只听 localhost | `host: '0.0.0.0'` |
| node_modules 二进制不匹配 | 宿主机覆盖了容器内 | 匿名卷 `/app/node_modules` |
| 命名冲突 ignored | 同名 .vue 在不同目录 | 重命名文件 + 引用处 |
| Dockerfile.dev 构建后 HMR 不生效 | `COPY . .` 把源码烤进镜像，覆盖挂载 | dev Dockerfile 不要 `COPY . .`，源码全靠挂载 |

---

## 七、Playwright 验证（捕获控制台错误）

用于验证 dev server 启动后无运行时错误：

```bash
node --input-type=module -e "
import { createRequire } from 'module';
const require = createRequire(process.env.APPDATA + '/npm/node_modules/');
const { chromium } = require('playwright');
const b = await chromium.launch({headless:true});
const p = await b.newPage();
const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('requestfailed',r=>errs.push(r.url()+' '+r.failure()?.errorText));
const r = await p.goto('http://localhost:6211/',{waitUntil:'networkidle',timeout:60000});
console.log('HTTP:',r?.status(),'URL:',p.url());
console.log(errs.length?errs.join('\n'):'(0 errors)');
await b.close();
"
```

前置：`npm install -g playwright && npx playwright install chromium`
