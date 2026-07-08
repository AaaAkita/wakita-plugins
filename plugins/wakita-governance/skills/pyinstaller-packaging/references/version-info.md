# Windows 版本信息嵌入

PyInstaller 通过 `--version-file` 参数将版本信息嵌入 .exe。

## file_version_info.txt 模板

新建 `file_version_info.txt`，填入以下内容并修改标注项：

```
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),       # 版本号：主.次.修订.构建
    prodvers=(1, 0, 0, 0),       # 产品版本号
    mask=0x3f,
    flags=0x0,
    OS=0x40004,                    # NT_WINDOWS32
    fileType=0x1,                  # VFT_APP
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',               # 语言：中文(简体)
        [
          StringStruct(u'CompanyName', u'你的公司名'),
          StringStruct(u'FileDescription', u'你的程序描述'),
          StringStruct(u'FileVersion', u'1.0.0.0'),
          StringStruct(u'InternalName', u'MyApp.exe'),
          StringStruct(u'LegalCopyright', u'Copyright (c) 2024'),
          StringStruct(u'OriginalFilename', u'MyApp.exe'),
          StringStruct(u'ProductName', u'你的产品名'),
          StringStruct(u'ProductVersion', u'1.0.0.0'),
        ]),
    ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])]),  # 中文
  ]
)
```

## 使用

```bash
pyinstaller --onefile --version-file=file_version_info.txt main.py
```

右键 .exe → 属性 → 详细信息，即可看到嵌入的版本号。

## 版本号自动化

如果通过 build.py 控制版本号，可以用 Python 替换模板里的 `filevers`、`FileVersion`、`ProductVersion` 字段：

```python
import re
version = "2.1.5"
nums = version.split(".")
with open("file_version_info.txt", "r+", encoding="utf-8") as f:
    text = f.read()
    text = re.sub(r"filevers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)",
                  f"filevers=({nums[0]}, {nums[1]}, {nums[2]}, {nums[3] if len(nums)>3 else '0'})",
                  text)
    text = re.sub(r"u'FileVersion', u'[^']*'", f"u'FileVersion', u'{version}.0'", text)
    text = re.sub(r"u'ProductVersion', u'[^']*'", f"u'ProductVersion', u'{version}.0'", text)
    f.seek(0); f.truncate(); f.write(text)
```
