---
name: frontend-docker-dev
description: 容器化前端开发模式配置。当需要把前端项目跑进 Docker 做 dev server + HMR、遇到 Vite/esbuild 在容器内崩溃、或 504 Outdated Optimize Dep 报错时使用。
metadata:
  short-description: 容器化前端开发模式与 Vite/esbuild 排错
---

# 容器化前端开发模式

把前端从「构建镜像 + nginx 静态」改为「挂载源码 + Vite dev server + HMR」，改代码即时生效免重建镜像。

## 何时触发

- 用户要把前端跑进 Docker 开发（HMR、热重载）
- Vite dev 在容器内崩溃：`The service was stopped`
- 浏览器报 `504 Outdated Optimize Dep`
- 动态 import 的模块加载失败、Vue Router 启动报错
- 前端 `Dockerfile.dev` / `docker-compose.override.yml` 配置

## 完整配置（三件套）

### 1. Dockerfile.dev（开发镜像，不用生产 Dockerfile）

```dockerfile
ARG REGISTRY=docker.io
FROM ${REGISTRY}/library/node:20-slim  # ⚠️ 用 slim(glibc) 不用 alpine(musl)

WORKDIR /app
RUN npm config set registry https://registry.npmmirror.com  # 国内源

COPY package*.json ./
# 缓存挂载持久化 npm 包，重构不重下
RUN --mount=type=cache,target=/root/.npm \
    npm install --prefer-offline --no-audit

EXPOSE 5173
CMD ["npm", "run", "dev"]
```

### 2. docker-compose.override.yml（自动加载，覆盖生产配置）

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports: !override           # 整体替换端口映射，避免冲突
      - "6211:5173"
    volumes:
      - ./frontend:/app        # 挂载源码，改代码触发 HMR
      - /app/node_modules      # 匿名卷隔离，防止宿主机(Win)二进制覆盖容器(Linux)
    shm_size: "1gb"            # ⚠️ 必加，默认 64MB 不足 esbuild 长驻服务
    environment:
      VITE_BACKEND_URL: http://backend:8000  # 容器内用服务名访问后端
    depends_on:
      backend:
        condition: service_started  # dev 模式不等 healthy
```

启动：`docker compose up`（自动合并 override）
生产：`docker compose -f docker-compose.yml up --no-override`

### 3. vite.config.ts（dev server 配置）

```ts
server: {
  host: '0.0.0.0',  // ⚠️ 必加，否则容器外访问不到（默认只听 localhost）
  port: 5173,
  proxy: {
    '/api': {
      target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',  // 容器内用服务名
      changeOrigin: true,
      ws: true
    }
  }
}
```

## 三大坑与根治

### 坑 1：esbuild `The service was stopped`

**症状**：Vite 启动 ready，但日志报 esbuild 崩溃，页面 504。

**根因**：esbuild 长驻服务（socket 通信）在 Docker 容器内不稳定。

**根治**（缺一不可）：
1. dev 镜像用 `node:20-slim`（glibc），**不用 `node:20-alpine`**（musl）。esbuild 无 musl 专用包，glibc 二进制在 musl 上更不稳。
2. 升级 esbuild 到 0.25+（package.json 显式声明，覆盖 vite 传递的旧版 0.21.x）。新版修复了容器内 socket 崩溃。
   ```bash
   npm install esbuild@latest --save
   ```
3. compose 加 `shm_size: "1gb"`（默认 64MB 偏小）。

### 坑 2：`504 Outdated Optimize Dep`

**症状**：浏览器加载页面时大量 504，动态 import 的模块（如 `views/Dashboard.vue`）加载失败，Vue Router 启动报错。

**根因**：按需引组件样式（`element-plus/es/components/<x>/style/css`）在运行时被动态发现，Vite 触发二次预构建 → esbuild 崩 → 504。`optimizeDeps.include` 无法完整覆盖（v-loading 指令、ElMessage 等 service 组件的样式总会遗漏）。

**根治**：组件 JS 按需，样式全量引入一次。
```ts
// vite.config.ts — Resolver 关闭按需样式
AutoImport({ resolvers: [ElementPlusResolver({ importStyle: false })] })
Components({ resolvers: [ElementPlusResolver({ importStyle: false })] })

// optimizeDeps.include 只放 JS 模块（CSS 不能放，会报 Cannot optimize）
optimizeDeps: {
  include: ['element-plus', 'element-plus/es', '@element-plus/icons-vue']
}
```
```ts
// main.ts — 全量引一份样式
import 'element-plus/dist/index.css'
```
这样不再有按组件的动态样式 import → 不触发二次预构建 → 不 504。组件 JS 仍按需（省 JS 体积）。

### 坑 3：组件命名冲突

**症状**：`[unplugin-vue-components] component "X" has naming conflicts, ignored`。

**根因**：不同目录下同名 `.vue` 文件，自动注册时冲突，一个被忽略。

**根治**：重命名其中一个（文件名 + 引用处），别用别名绕（别名治标，冲突仍在）。

## 验证方法（Playwright 捕获控制台）

```bash
node --input-type=module -e "
import { createRequire } from 'module';
const require = createRequire('C:/Users/Administrator/AppData/Roaming/npm/node_modules/');
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
`playwright` 需全局装：`npm install -g playwright && npx playwright install chromium`

## 排错速查表

| 症状 | 根因 | 修复 |
|------|------|------|
| `The service was stopped` | esbuild 长驻服务在容器内崩 | slim 镜像 + esbuild 升级 + shm_size |
| `504 Outdated Optimize Dep` | 按需样式触发二次预构建 | 样式全量引入，importStyle:false |
| `Cannot optimize dependency: xxx.css` | CSS 放进了 optimizeDeps.include | include 只放 JS，CSS 用 import |
| 页面白屏、容器外访问不到 | dev server 只听 localhost | host: '0.0.0.0' |
| node_modules 二进制不匹配 | 宿主机覆盖了容器内 | 匿名卷 `/app/node_modules` |
| 命名冲突 ignored | 同名 .vue 在不同目录 | 重命名文件 + 引用处 |
