---
name: test-quality-principles
description: >
  测试质量铁律与验证证据真实性：先读实现再写测试、测行为不测实现、失败路径必测、
  Mock 依赖不 Mock 被测对象；含假绿/PIPESTATUS/格式化污染/本地未复现。
when_to_use: >
  写测试、单元测试、测试用例、测试覆盖、pytest、jest、vitest、测试规范、测试质量、
  测试原则、unit test、write test、test quality、test principle、mocking、test coverage、
  假绿、PIPESTATUS、测试全过但线上坏、格式化范围、本地验证。
---

# 测试质量原则 — Test Quality Principles

> 写测试前必须读被测代码的真实实现，确保测试验证的是正确行为，而非复刻 Bug。

## 触发条件

编写新测试、修改现有测试、审查测试代码时自动适用。

## 四条铁律

### 1. 先读实现再写测试

测试断言必须与代码的**真实设计意图**对齐，不能仅匹配当前输出。

**❌ 错误示范**（测试跟着 Bug 一起写错了）：

```python
# field_maps.py 中 title 被错误放在 desc 前面
"content": {"candidates": ["title", "question_title", "desc", "content"]}

# 测试断言了 Bug 行为
assert standard["content"] == raw["title"]   # Bug！
```

**✅ 正确做法**：先确认 `desc` 才是正文字段，再写：

```python
assert standard["content"] == raw["desc"]     # 正确！
```

**验证方法**：读被测函数的调用链——数据从哪里来？字段名在上下游叫什么？不只看函数签名。

---

### 2. 测行为不测实现

测试验证 **"做了什么"**（调了 commit、派发了任务），不验证 **"怎么做的"**（调了 flush、用了 async）。

**❌ 错误**：测内部实现细节

```python
# Python
mock_db.flush.assert_called()   # 脆弱，换 ORM 就挂

# JavaScript
expect(container.querySelector('.spinner')).toBeNull()  # 脆弱，换 UI 库就挂
```

**✅ 正确**：测外部可观察行为

```python
# Python
mock_db.commit.assert_awaited_once()   # 验证事务提交

# JavaScript
expect(mockTaskApi.start).toHaveBeenCalledWith(99)  # 验证爬虫被派发

# 任何语言
expect(response.status).toBe(200)                   # 验证接口返回状态
expect(db.query("SELECT COUNT(*) FROM orders").one()[0]).toBe(3)  # 验证数据结果
```

---

### 3. 失败路径必测

正常路径测试再多也防不住异常分支。**每个 `if/except/return None` 分支至少一个测试。**

| 必须覆盖的失败场景 | 示例 |
|---|---|
| 依赖返回 None/空 | Repository 查不到记录 → 方法正确 fallback |
| 外部调用抛异常 | API 调用失败 → 不崩溃，返回错误信息 |
| 输入为边界值 | 空列表、超长字符串、null、undefined |
| 事务异常回滚 | 写入失败 → rollback 被调用 |
| 权限不足 | 未认证用户访问需权限接口 → 403 |

**验证方法**：数被测函数的 `if/except/return None/raise` 分支，每个分支至少一个测试。

**对称场景全覆盖**：修复一个影响多个对称方向的 bug 后，**每个方向都要单独写测试**，不要只测一个方向就认为全修好了。

```text
错误路径：
  修复了大小写匹配 bug（影响 top/bottom/left/right 四个方向）
  → 只写了"纵向缩放生效"的测试
  → 横向没测
  → 横向其实坏了，但本地测试全过
  → 用户实测才发现

正确路径：
  修复后，bottomRight 的横向、bottomRight 的纵向、
  topLeft 的横向、topLeft 的纵向，各写一个测试
  → 本地就能抓到"横向没修好"
  → 不用转嫁验证成本给用户
```

> 这适用于所有对称场景：CRUD 四操作、文件导入/导出、编码/解码、序列化/反序列化、push/pop、展开/折叠等。

---

### 4. Mock 依赖，不 Mock 被测对象

测试的目标是验证被测代码，不是验证 Mock 框架。

| 被测层 | Mock 这一层 | 不 Mock |
|--------|-----------|---------|
| Service / UseCase | Repository、外部 API、外部 Service | Service 自身的方法 |
| API 端点 / Controller | Service | 端点自身的处理函数 |
| 前端组件 | API 模块、Store、路由 | 组件自身的逻辑方法 |

**❌ 错误**：

```python
# Python —— Mock 了被测方法本身，什么都没测
svc.import_cookie = AsyncMock()

# JavaScript —— Mock 了组件自己的方法
wrapper.vm.handleSubmit = jest.fn()
```

**✅ 正确**：

```python
# Python —— Mock 依赖的 Repository
svc.cookie_repository.upsert_cookie = AsyncMock()
result = await svc.import_cookie("zhihu", "test", 1)  # 测真实方法

# JavaScript —— Mock 依赖的 API 模块
mockApi.createOrder.mockResolvedValue({ id: 1 })
result = await service.submitOrder({ items: [] })     # 测真实方法
```

---

## 验证证据的真实性（别把假绿当通过）

本地验证的结论必须经得起复核，以下四类假象都真实发生过。

### 1. 管道退出码假象

```bash
# ❌ $? 是管道末端 head 的退出码，恒为 0
pytest | grep FAIL | head; echo "EXIT=$?"
# ✅ 用 PIPESTATUS 取被测命令本身，或干脆不接管道
pytest; echo "EXIT=$?"
```

报告「测试通过」前必须确认：失败行数为 0，且被测命令自身退出码为 0。
「grep 没输出」不等于「测试通过」——也可能命令根本没跑。

### 2. 格式化工具的污染范围

只对本次改动的文件（或项目规定的目录）跑格式化。对历史未格式化目录全量跑
`black/isort/prettier`，会制造几十个无关 diff 混进功能提交，审查时无法区分真实改动。
误跑后逐文件对比「HEAD 内容格式化结果」与「工作区内容」，相等即纯格式化 → 回退。

### 3. 本地复现要贴近生产

修复部署/迁移类问题时，用与生产同版本的镜像、同结构的库在本地复现；
不要把「单元测试过了」当部署验证。验证证据（命令 + 真实输出 + 关键数字）先给用户看，
确认后再推送。

### 4. 全绿测试不等于契约覆盖

空分支、异常分支手写的兜底 payload 往往没有测试覆盖；响应模型新增必填字段时，
这些分支会在运行时 500。加字段时必须补「空/兜底 payload 过模型校验」的守护测试。

## 审查判据（被 clean-home 的验证步骤加载时）

- **D1 测试存在性**：核心逻辑有没有测试？关键路径有没有集成/E2E？核心逻辑无测试 → P0；覆盖不足 → P1。
- **证据缺失**：没有测试、没跑过、只看到声明没看到输出 → 记「证据缺失」，不要当成通过。
- **AI 特有假象**：测试只断言当前实现、只覆盖快乐路径、Mock 了被测对象本身——按上文四条铁律判定；更细的 AI 生成失败模式见 `ai-code-failure-modes`。
- **守护测试是否生效**：新增的令牌/断点/lint/CI 守护测试是否已提交、纳入 CI、当前为绿？只创建不提交、CI 不跑、规范文档缺失、或当前红，都记「证据缺失」或单列过程问题；不要因为「有测试文件」就认为有守护。

## 检查清单（写测试前逐项确认）

- [ ] 我读了被测函数及其全部调用链的代码
- [ ] 我确认了输入数据的真实字段名和类型（不是猜测）
- [ ] 我覆盖了正常路径 + 至少 2 个失败/边界路径 + 对称场景全方向
- [ ] 我 Mock 的是依赖，不是被测对象本身
- [ ] 我的断言验证的是可观察行为，不是内部实现
- [ ] 我跑过测试覆盖检查，确认新增行被覆盖且无 side effect
