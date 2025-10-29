# A股智能投顾助手 - PowerShell 启动脚本
# 使用方法: .\scripts\start_powershell.ps1

Write-Host "🚀 启动A股智能投顾助手..." -ForegroundColor Green

# 检查环境变量配置
if (-not (Test-Path "backend\.env")) {
    Write-Host "❌ 后端环境变量文件不存在，请先运行 setup_windows.bat 或 setup_powershell.ps1" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 检查虚拟环境
if (-not (Test-Path "backend\venv")) {
    Write-Host "❌ Python虚拟环境不存在，请先运行 setup_windows.bat 或 setup_powershell.ps1" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 检查Node.js依赖
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "❌ 前端依赖未安装，请先运行 setup_windows.bat 或 setup_powershell.ps1" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 启动后端
Write-Host "🔧 启动后端服务..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location backend
    & .\venv\Scripts\Activate.ps1
    uvicorn main:app --reload --host 127.0.0.1 --port 8000
}

# 等待后端启动
Write-Host "⏳ 等待后端服务启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 启动前端
Write-Host "🎨 启动前端服务..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    Set-Location frontend
    npm run dev
}

Write-Host ""
Write-Host "✅ 服务启动完成！" -ForegroundColor Green
Write-Host "📱 前端地址: http://localhost:5173" -ForegroundColor White
Write-Host "📊 后端API: http://localhost:8000" -ForegroundColor White
Write-Host "📖 API文档: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "💡 提示：" -ForegroundColor Yellow
Write-Host "- 按 Ctrl+C 停止服务" -ForegroundColor White
Write-Host "- 如有问题，请检查浏览器控制台和后端日志" -ForegroundColor White
Write-Host ""
Write-Host "🌐 正在打开浏览器..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

try {
    # 等待用户中断
    Write-Host "按 Ctrl+C 停止所有服务..." -ForegroundColor Cyan
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
catch {
    Write-Host "`n🛑 正在停止服务..." -ForegroundColor Yellow
}
finally {
    # 停止所有后台任务
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $frontendJob -ErrorAction SilentlyContinue
    Write-Host "✅ 服务已停止" -ForegroundColor Green
}