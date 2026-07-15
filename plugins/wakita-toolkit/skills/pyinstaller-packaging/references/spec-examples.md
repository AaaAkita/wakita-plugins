# .spec 文件常见定制

## 排除不需要的模块

减小打包体积，排除误拖入的大型库：

```python
a = Analysis(['main.py'],
    # ...
    excludes=['tkinter', 'unittest', 'email', 'html', 'xml', 'pydoc'],
    # ...
)
```

## 排除特定文件的 copy

```python
a = Analysis(['main.py'],
    # 排除测试文件
    exclude_datas=[('**/tests/*', '')],
    # ...
)
```

## 嵌入额外二进制/DLL

PyInstaller 没自动检测到的 .dll/.pyd 文件：

```python
a = Analysis(['main.py'],
    binaries=[('C:/path/to/extra.dll', '.')],
    # ...
)
```

## 带 Chromium/CEF 的程序

如果你的程序内嵌浏览器（如 Playwright/Cefpython），需要手动收集浏览器文件：

```python
# 收集 Playwright 浏览器
import playwright
import os

playwright_dir = os.path.dirname(playwright.__file__)

a = Analysis(['main.py'],
    datas=[
        (os.path.join(playwright_dir, 'driver'), 'playwright/driver'),
    ],
    # ...
)
```

更完整的做法是将浏览器目录放在 .exe 同级目录而非打包进去：
1. 先用 `--onedir` 打包
2. 手动将浏览器目录（如 `ms-playwright/chromium-*/`）复制到 dist/ 同级
3. 代码里 `resource_path()` 指向同级目录

## 构建后自动化

在 .spec 文件末尾加钩子，构建完成后自动执行：

```python
# 构建
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, ...)

# 构建后：复制额外文件
import shutil, os
dist_dir = os.path.dirname(exe.name)
shutil.copy('config.json', dist_dir)
shutil.copytree('assets', os.path.join(dist_dir, 'assets'), dirs_exist_ok=True)

# 构建后：压缩为 zip
import zipfile
version = '1.0.0'
zip_name = f'MyApp_v{version}.zip'
with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(dist_dir):
        for file in files:
            full = os.path.join(root, file)
            arc = os.path.relpath(full, os.path.dirname(dist_dir))
            zf.write(full, arc)
```
