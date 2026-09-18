# SFLS Sports Meeting System - Offline Deployment Package Builder (Windows)

Write-Host "=== SFLS Sports Meeting System - Package Builder ===" -ForegroundColor Cyan
Write-Host ""

# 1. Build images
Write-Host "[1/4] Building images..." -ForegroundColor Yellow
docker compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to build images" -ForegroundColor Red
    exit 1
}

docker compose pull mysql
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to pull mysql image" -ForegroundColor Red
    exit 1
}

# 2. Export images
Write-Host "[2/4] Exporting images..." -ForegroundColor Yellow
docker save -o sfls-images.tar sport-meeting-backend:latest sport-meeting-frontend:latest mysql:8.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to export images" -ForegroundColor Red
    exit 1
}

# 3. Package minimal runtime files (only 3 files needed)
Write-Host "[3/4] Packaging runtime files..." -ForegroundColor Yellow
if (Test-Path sfls-runtime.tar.gz) { Remove-Item sfls-runtime.tar.gz }
tar -czf sfls-runtime.tar.gz docker-compose.yml .env.example DEPLOYMENT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to create runtime package" -ForegroundColor Red
    exit 1
}

# 4. Create deployment package directory
Write-Host "[4/4] Creating final deployment package..." -ForegroundColor Yellow
if (Test-Path deploy-package) { Remove-Item -Recurse -Force deploy-package }
New-Item -ItemType Directory -Path deploy-package | Out-Null
Move-Item sfls-images.tar deploy-package/
Move-Item sfls-runtime.tar.gz deploy-package/

# Generate README with UTF-8 encoding (no BOM)
$readmeContent = @"
SFLS Sports Meeting System - Offline Deployment Package
========================================================

This package contains:
  sfls-images.tar       - Docker images (~500MB-1GB)
  sfls-runtime.tar.gz   - Runtime config files (<10KB)

Deployment steps (on target server):
  1. Extract runtime files:
     mkdir sport-meeting && cd sport-meeting
     tar -xzf /path/to/sfls-runtime.tar.gz

  2. Configure environment:
     cp .env.example .env
     # Edit .env, at least modify:
     #   MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD
     #   JWT_SECRET / ADMIN_PASSWORD
     #   APP_PORT (default 8687)

  3. Load images:
     docker load -i /path/to/sfls-images.tar

  4. Start services:
     docker compose up -d --no-build

For detailed instructions, see DEPLOYMENT.md (Chinese)
"@

# Use .NET method to write UTF-8 without BOM
[System.IO.File]::WriteAllText("deploy-package/README.txt", $readmeContent, (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
Write-Host "SUCCESS: Deployment package created in deploy-package/ directory" -ForegroundColor Green
Write-Host "   - sfls-images.tar (Docker images)" -ForegroundColor Gray
Write-Host "   - sfls-runtime.tar.gz (Config files, only 3 files)" -ForegroundColor Gray
Write-Host "   - README.txt (Deployment instructions)" -ForegroundColor Gray
Write-Host ""
Write-Host "Copy the entire deploy-package/ directory to your server" -ForegroundColor Green
