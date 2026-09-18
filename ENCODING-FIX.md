# Windows 编码问题解决方案

## 问题现象

在 Windows PowerShell 中运行包含中文的脚本时出现乱码，且生成的文件在 Linux 服务器上显示乱码。

## 根本原因

**PowerShell 的双重编码问题**：

1. **脚本文件本身的编码**
   - VS Code/Claude 保存脚本为 UTF-8
   - PowerShell 5.1 默认用 GBK 读取脚本
   - 结果：脚本中的中文显示为乱码

2. **脚本输出的编码**
   - `Out-File -Encoding UTF8` 在 PowerShell 5.1 中写入 UTF-8 with BOM
   - Linux 服务器期望 UTF-8 without BOM
   - 结果：生成的文件在 Linux 上显示乱码

## 完整解决方案

### ✅ 方案 1：全英文脚本（已采用）

**最可靠的方案**：脚本本身用英文，避免编码问题。

- ✅ `deploy-package.ps1` — 重写为全英文
- ✅ 生成的 `README.txt` 使用 `[System.IO.File]::WriteAllText` 强制 UTF-8 无 BOM
- ✅ 在任何 PowerShell 版本上都能正常运行

```powershell
# 直接运行，无需任何配置
.\deploy-package.ps1
```

### 方案 2：使用 Git Bash / WSL（推荐）

Linux 环境原生 UTF-8，零编码问题：

```bash
bash deploy-package.sh
```

### 方案 3：升级到 PowerShell 7+

PowerShell 7+ 默认使用 UTF-8：

1. 下载安装：https://github.com/PowerShell/PowerShell/releases
2. 使用 `pwsh` 命令运行脚本

```powershell
pwsh -File deploy-package.ps1
```

### 方案 4：设置 PowerShell 5.1 编码（不推荐）

在运行脚本前临时设置：

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001  # 切换到 UTF-8 代码页

.\deploy-package.ps1
```

**缺点**：每次运行前都要设置，容易忘记。

## 技术细节

### PowerShell 版本差异

| 版本 | 脚本读取编码 | Out-File 编码 | 推荐度 |
|------|-------------|--------------|--------|
| PowerShell 5.1 (Windows 内置) | GBK/ANSI | UTF-8 with BOM | ⚠️ 需要处理 |
| PowerShell 7+ (跨平台) | UTF-8 | UTF-8 without BOM | ✅ 推荐 |

查看当前版本：

```powershell
$PSVersionTable.PSVersion
```

### 正确的 UTF-8 写入方法

```powershell
# ❌ 错误：PowerShell 5.1 会加 BOM
$content | Out-File -FilePath file.txt -Encoding UTF8

# ✅ 正确：强制 UTF-8 无 BOM
[System.IO.File]::WriteAllText(
    "file.txt",
    $content,
    (New-Object System.Text.UTF8Encoding $false)  # $false = 无 BOM
)
```

## 验证编码

### 方法 1：运行测试脚本

```powershell
.\test-encoding.ps1
```

会生成三种编码的测试文件到 `encoding-test/` 目录，用记事本或 VS Code 打开对比。

### 方法 2：检查文件编码

**Windows PowerShell**：

```powershell
Get-Content deploy-package/README.txt -Encoding UTF8
```

**Git Bash / Linux**：

```bash
file -i deploy-package/README.txt
# 应显示：charset=utf-8
```

**VS Code**：
- 右下角显示文件编码
- 应为 `UTF-8` 而非 `UTF-8 with BOM`

## 已修复的文件

✅ **`deploy-package.ps1`**
- 脚本内容改为全英文，避免读取编码问题
- 使用 `[System.IO.File]::WriteAllText` 生成 UTF-8 无 BOM 的 README.txt
- 添加错误处理和退出码

✅ **`test-encoding.ps1`**
- 全英文脚本
- 用于测试三种编码方法的效果

📄 **`编码说明.md`** (本文件)
- 详细的问题分析和解决方案
- 可作为团队知识库参考

## 最佳实践

### 对于本项目

1. **生产部署**：优先使用 `bash deploy-package.sh`（Git Bash / WSL / Linux）
2. **Windows 环境**：使用修复后的 `deploy-package.ps1`
3. **团队协作**：文档和配置文件使用英文，避免编码问题

### 对于未来的脚本开发

1. **脚本命令**：优先用英文，或用 PowerShell 7+
2. **生成文件**：如需生成包含中文的文件，使用 `[System.IO.File]::WriteAllText` 方法
3. **跨平台**：同时提供 `.sh` (Linux/Mac) 和 `.ps1` (Windows) 版本

## 相关资源

- PowerShell 7 下载：https://github.com/PowerShell/PowerShell/releases
- UTF-8 编码说明：https://www.utf8-chartable.de/
- BOM 问题解释：https://en.wikipedia.org/wiki/Byte_order_mark

## 总结

**当前状态**：✅ 编码问题已完全解决

- 脚本使用英文，在任何 PowerShell 版本都能正常运行
- 生成的 README.txt 使用 UTF-8 无 BOM，在 Linux 服务器显示正常
- 提供测试工具验证编码正确性

**立即可用**：

```powershell
.\deploy-package.ps1
```

生成的部署包可直接在 Linux 服务器上使用！
