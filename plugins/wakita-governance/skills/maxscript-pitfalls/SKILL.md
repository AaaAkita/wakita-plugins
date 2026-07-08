---
name: maxscript-pitfalls
description: |
  当用户正在编写、修改或调试 3ds Max MaxScript 脚本时，必须使用本 skill。
  本 skill 记录了 MaxScript 开发过程中踩过的坑和解决方案，
  涉及语法陷阱、API 差异、文件路径处理、材质贴图遍历等关键知识点。
  适用于 rename_textures_v2.ms 等材质/贴图处理脚本的维护与迭代。
---

# MaxScript 踩坑记录

## 一、语法陷阱

### 1.1 顶层代码不能用 `local`

MaxScript 的**顶层代码（函数外部）**不能用 `local` 声明变量，只会在函数内部或块级作用域生效。

```maxscript
-- ❌ 错误
local fullSavePath = maxFilePath + maxFileName

-- ✅ 正确
fullSavePath = maxFilePath + maxFileName
```

**报错信息**：`Compile error: no local declarations at top level`

### 1.2 没有 `+=` 运算符

MaxScript 不支持 `+=`、`-=` 等复合赋值运算符。

```maxscript
-- ❌ 错误
matRenamedCount += 1

-- ✅ 正确
matRenamedCount = matRenamedCount + 1
```

### 1.3 `if` 语句的语法

单行 `if` 后面如果有多条语句，必须用括号包裹。

```maxscript
-- ❌ 错误（多语句未包裹）
if cond then a = a + 1; b = b + 1

-- ✅ 正确
if cond then (
    a = a + 1
    b = b + 1
)

-- 或者使用三元表达式
result = if cond then val1 else val2
```

### 1.4 字符串拼接用 `+`

```maxscript
newName = prefix + "-" + indexStr + suffix
```

### 1.5 不支持行首 `+` 续行

MaxScript 不支持把 `+` 放在行首作为续行符，会报 `expected <factor>`。

```maxscript
-- ❌ 错误
logText = logText + "part1"
        + "part2"

-- ✅ 正确：写在一行
logText = logText + "part1" + "part2"
```

### 1.6 .NET DataGridView 索引必须用 `.Item`，不能用 `[]`

MaxScript 不支持 C# 风格的字符串索引器 `columns["name"]`，必须用 `.Item` 方法。

```maxscript
-- ❌ 错误
dgv.Columns["colCheck"].ReadOnly = false
dgv.Rows[i].Cells["colCheck"].Value = true

-- ✅ 正确
dgv.Columns.Item "colCheck" .ReadOnly = false
(dgv.Rows.Item i).Cells.Item "colCheck" .Value = true
```

### 1.7 .NET 链式调用避免空格分割

`(dgv.Rows.Item i).Cells.Item "colCheck" .Value` 中间的空格会让 MaxScript 误解析 `.Value` 为独立表达式。

```maxscript
-- ❌ 错误（空格导致解析失败）
(dgv.Rows.Item i).Cells.Item "colCheck" .Value = true

-- ✅ 正确：拆分为局部变量
local theRow = dgv.Rows.Item i
(theRow.Cells.Item "colCheck").Value = true
```

## 二、文件路径处理

### 2.1 `maxFilePath` vs `maxFileName`

| 全局变量 | 内容 | 示例 |
|---------|------|------|
| `maxFilePath` | 仅目录路径（含末尾 `\`） | `E:\Project\` |
| `maxFileName` | 仅文件名 | `scene.max` |

```maxscript
-- ❌ 错误：保存后丢失文件名
saveMaxFile maxFilePath quiet:true

-- ✅ 正确
fullPath = maxFilePath + maxFileName
saveMaxFile fullPath quiet:true
```

### 2.2 解析相对路径用 `mapPaths.getFullFilePath`

```maxscript
-- ❌ 错误：方法不存在
resolved = mapPaths.resolvePath relPath

-- ✅ 正确
resolved = mapPaths.getFullFilePath relPath
```

### 2.3 `getFilenamePath` 返回含末尾分隔符的路径

```maxscript
dir = getFilenamePath "E:\\Project\\tex.png"
-- 结果："E:\\Project\\"

newPath = dir + "newName.png"
-- 结果："E:\\Project\\newName.png" ✅ 正确
```

## 三、材质与贴图遍历

### 3.1 `sceneMaterials` 里混有非材质节点

`sceneMaterials` 不只是材质，贴图节点（BitmapTexture、VRayBitmap）也可能出现在里面，必须过滤。

```maxscript
for mat in sceneMaterials do (
    if mat == undefined then continue
    
    -- 跳过贴图节点
    local cls = classOf mat
    if cls == BitmapTexture or cls == VRayBitmap or cls == CoronaBitmap then continue
    if superclassOf mat != material then continue
    
    -- 处理材质...
)
```

### 3.2 `getClassInstances` 的 `target:` 参数

```maxscript
-- 只获取绑定到特定材质的贴图节点
bitmaps = getClassInstances BitmapTexture target:mat
```

### 3.3 贴图可能嵌套在中间节点中

贴图可能不直接放在材质 slot 上，而是嵌套在 `VRayNormalMap`、`Falloff`、`ColorCorrection` 等中间节点里。需要递归查找。

```maxscript
fn findBitmapInMap parentMap bitmapNode visited = (
    if parentMap == undefined then return false
    if parentMap == bitmapNode then return true
    if findItem visited parentMap > 0 then return false
    append visited parentMap
    
    local props = getPropNames parentMap
    for p in props do (
        try (
            local val = getProperty parentMap p
            if val == bitmapNode then return true
            if superclassOf val == textureMap or superclassOf val == material then (
                if findBitmapInMap val bitmapNode visited then return true
            )
        ) catch ()
    )
    false
)
```

### 3.4 Standardmaterial 的贴图可能在 `.maps` 数组里

从外部导入的模型，Standardmaterial 的贴图可能放在 `.maps` 数组中而非单独属性上。

```maxscript
-- 后备：遍历 maps 数组
for i = 1 to mat.maps.count do (
    local val = mat.maps[i]
    if val == bitmapNode then return mapNames[i]
    if val != undefined and findBitmapInMap val bitmapNode #() then return mapNames[i]
)
```

## 四、属性访问安全

### 4.1 材质属性可能不存在

不同版本的 V-Ray 创建的 VRayMtl，属性集合可能不同。访问不存在的属性会直接报错。

```maxscript
-- ❌ 危险：直接访问
if mat.metalness > 0 then return "MR"

-- ✅ 安全：用 try-catch 包裹
try (
    if mat.metalness != undefined and mat.metalness > 0 then return "MR"
) catch ()
```

## 五、文件操作

### 5.1 用 .NET 类复制文件

MaxScript 自带的 `copyFile` 功能有限，推荐用 .NET：

```maxscript
(dotNetClass "System.IO.File").Copy srcPath dstPath
```

### 5.2 复制前检查文件是否存在

```maxscript
if not doesFileExist srcPath then (
    format "[跳过] 源文件不存在: %\n" srcPath
    return false
)
if doesFileExist dstPath then (
    format "[跳过] 目标文件已存在: %\n" dstPath
    return false
)
```

## 六、保存与退出

### 6.1 `quitMAX` 会导致 3dsmaxbatch 挂起

在脚本末尾不要调用 `quitMAX #noPrompt`，否则批处理模式会卡死。

```maxscript
-- ❌ 危险
quitMAX #noPrompt

-- ✅ 正确：只保存，不退出
saveMaxFile fullPath quiet:true
```

## 七、常见材质类型判断

```maxscript
local matClass = classOf mat

case matClass of (
    VrayMtl: "V-Ray"
    Standardmaterial: "Standard"
    PhysicalMaterial: "Physical"
    CoronaMtl: "Corona"
    default: "Unknown"
)
```

## 八、工作流检测（MR vs SG）

| 材质类型 | MR 标志 | SG 标志 |
|---------|---------|---------|
| VRayMtl | `texmap_metalness` 存在，或 `metalness > 0` | 无 metalness 相关属性 |
| PhysicalMaterial | 固定 MR | - |
| Standardmaterial | 固定 SG | - |
| CoronaMtl | `texmapMetallic` 存在 | 无 |

## 九、调试技巧

### 9.1 在监听器中打印变量

```maxscript
format "变量值: %\n" myVariable
```

### 9.2 检查对象类型

```maxscript
classOf obj        -- 精确类名
superclassOf obj   -- 父类（如 material、textureMap）
```

### 9.3 查看对象所有属性

```maxscript
getPropNames obj
```

### 9.4 查看对象属性值

```maxscript
for p in getPropNames obj do (
    try (
        format "% = %\n" p (getProperty obj p)
    ) catch (
        format "% = <error>\n" p
    )
)
```
