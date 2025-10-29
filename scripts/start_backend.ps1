# A股智能投顾助手 - 启动后端服务 (PowerShell)
# 使用方法: .\scripts\start_backend.ps1

Write-Host "A股智能投顾助手 - 启动后端服务" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Yellow

# 检查是否在项目根目录
if (-not (Test-Path "backend")) {
    Write-Host "错误: 请在项目根目录运行此脚本" -ForegroundColor Red
    exit 1
}

# 检查虚拟环境
$venvDir = "backend\venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "错误: 未找到虚拟环境，请先运行 setup_powershell.ps1" -ForegroundColor Red
    exit 1
}

# 检查环境变量文件
$envFile = "backend\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "错误: 未找到.env文件，请先运行 setup_powershell.ps1" -ForegroundColor Red
    exit 1
}

# 检查Python可执行文件
$pythonExe = "$venvDir\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "错误: 未找到Python可执行文件: $pythonExe" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] 环境检查通过" -ForegroundColor Green
Write-Host "[START] 启动后端服务..." -ForegroundColor Yellow
Write-Host "[URL] 服务地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "[DOCS] API文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "[HEALTH] 健康检查: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host "-" * 50 -ForegroundColor Gray

# 切换到后端目录并启动服务
Set-Location backend

try {
    # 使用虚拟环境中的Python启动服务
    & $pythonExe main.py
} catch [System.Management.Automation.HaltCommandException] {
    # Ctrl+C 被按下
    Write-Host ""
    Write-Host "[STOP] 服务已停止" -ForegroundColor Yellow
} catch {
    Write-Host ""
    Write-Host "[ERROR] 服务启动失败: $_" -ForegroundColor Red
    exit 1
} finally {
    # 返回项目根目录
    Set-Location ..
}

Write-Host "脚本执行完成" -ForegroundColor Green