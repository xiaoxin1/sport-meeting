# SFLS Sports Meeting System - Encoding Test

Write-Host "=== Encoding Test ===" -ForegroundColor Cyan
Write-Host ""

# Test content (with Chinese characters)
$testContent = @"
Test Chinese Encoding
这是一段包含中文的测试文本
If displayed correctly, encoding is OK
"@

# Create test directory
$testDir = "encoding-test"
if (Test-Path $testDir) { Remove-Item -Recurse -Force $testDir }
New-Item -ItemType Directory -Path $testDir | Out-Null

Write-Host "Generating test files with different encodings..." -ForegroundColor Yellow

# Method 1: Out-File UTF8 (PowerShell 5.1 adds BOM)
$testContent | Out-File -FilePath "$testDir/test-outfile-utf8.txt" -Encoding UTF8

# Method 2: [System.IO.File]::WriteAllText UTF8 without BOM (Recommended)
[System.IO.File]::WriteAllText("$testDir/test-writealltext-utf8.txt", $testContent, (New-Object System.Text.UTF8Encoding $false))

# Method 3: Default encoding (usually GBK on Chinese Windows)
$testContent | Out-File -FilePath "$testDir/test-default.txt"

Write-Host ""
Write-Host "Test files created in $testDir/ directory:" -ForegroundColor Green
Write-Host "  - test-outfile-utf8.txt (Out-File UTF8)" -ForegroundColor Gray
Write-Host "  - test-writealltext-utf8.txt (WriteAllText UTF8 no BOM, recommended)" -ForegroundColor Gray
Write-Host "  - test-default.txt (Default encoding)" -ForegroundColor Gray
Write-Host ""

Write-Host "Verification steps:" -ForegroundColor Yellow
Write-Host "1. Open these files with Notepad/VS Code, check if Chinese displays correctly"
Write-Host "2. On Linux server use 'cat', test-writealltext-utf8.txt should display correctly"
Write-Host ""
Write-Host "Recommended: deploy-package.ps1 now uses WriteAllText UTF8 no BOM method" -ForegroundColor Green
