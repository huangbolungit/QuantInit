# A股智能投顾助手 - PowerShell 设置脚本
# 使用方法: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# .\scripts\setup_powershell.ps1

Write-Host "🚀 开始设置A股智能投顾助手开发环境 (PowerShell)..." -ForegroundColor Green

# 检查Python版本
Write-Host "📋 检查Python版本..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python未安装，请先安装Python 3.9或更高版本" -ForegroundColor Red
    Write-Host "📥 下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按任意键退出"
    exit 1
}

# 检查Node.js版本
Write-Host "📋 检查Node.js版本..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js版本: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js未安装，请先安装Node.js 16或更高版本" -ForegroundColor Red
    Write-Host "📥 下载地址: https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "按任意键退出"
    exit 1
}

# 设置后端环境
Write-Host "🔧 设置后端环境..." -ForegroundColor Yellow
if (Test-Path "backend") {
    Set-Location backend
    Write-Host "📍 进入后端目录: $(Get-Location)" -ForegroundColor Cyan

    # 检查必要文件
    if (-not (Test-Path "requirements.txt")) {
        Write-Host "❌ 未找到requirements.txt文件" -ForegroundColor Red
        Set-Location ..
        exit 1
    }
    if (-not (Test-Path ".env.example")) {
        Write-Host "❌ 未找到.env.example文件" -ForegroundColor Red
        Set-Location ..
        exit 1
    }
} else {
    Write-Host "❌ 未找到backend目录" -ForegroundColor Red
    exit 1
}

# 创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "📦 创建Python虚拟环境..." -ForegroundColor Cyan
    python -m venv venv
}

# 激活虚拟环境
Write-Host "🔄 激活虚拟环境..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# 升级pip
Write-Host "⬆️ 升级pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# 安装依赖
Write-Host "📦 安装Python依赖..." -ForegroundColor Cyan
pip install -r requirements.txt

# 创建环境变量文件
if (-not (Test-Path ".env")) {
    Write-Host "📝 创建环境变量文件..." -ForegroundColor Cyan
    Copy-Item .env.example .env
    Write-Host "⚠️  请编辑 backend\.env 文件，配置您的API密钥" -ForegroundColor Yellow
}

# 创建数据目录
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" }
if (-not (Test-Path "data\database")) { New-Item -ItemType Directory -Path "data\database" }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" }

# 返回根目录
Set-Location ..

# 设置前端环境
Write-Host "🔧 设置前端环境..." -ForegroundColor Yellow
if (Test-Path "frontend") {
    Set-Location frontend
    Write-Host "📍 当前目录: $(Get-Location)" -ForegroundColor Cyan

    # 检查package.json是否存在
    if (Test-Path "package.json") {
        Write-Host "✅ 找到package.json" -ForegroundColor Green
    } else {
        Write-Host "❌ 未找到package.json文件" -ForegroundColor Red
        Write-Host "📋 frontend目录内容:" -ForegroundColor Yellow
        Get-ChildItem
        Set-Location ..
        Write-Host "❌ 前端目录缺少package.json，请检查项目结构" -ForegroundColor Red
        Read-Host "按任意键退出"
        exit 1
    }
} else {
    Write-Host "❌ 未找到frontend目录" -ForegroundColor Red
    Write-Host "📋 当前目录内容:" -ForegroundColor Yellow
    Get-ChildItem
    exit 1
}

# 安装依赖
Write-Host "📦 安装Node.js依赖..." -ForegroundColor Cyan
try {
    npm install
    Write-Host "✅ Node.js依赖安装完成" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js依赖安装失败" -ForegroundColor Red
    Write-Host "📋 错误详情: $_" -ForegroundColor Yellow
    Set-Location ..
    Write-Host "🔧 尝试手动安装: cd frontend && npm install" -ForegroundColor Yellow
    Read-Host "按任意键继续"
}

# 创建环境变量文件
if (-not (Test-Path ".env")) {
    Write-Host "📝 创建前端环境变量文件..." -ForegroundColor Cyan
    @"
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_TITLE=A股智能投顾助手
VITE_APP_VERSION=0.2.0-MVP
"@ | Out-File -FilePath .env -Encoding UTF8
}

# 返回根目录
Set-Location ..

Write-Host ""
Write-Host "🎉 环境设置完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📋 下一步操作：" -ForegroundColor Yellow
Write-Host "1. 编辑 backend\.env 文件，配置您的GLM-4.6 API密钥" -ForegroundColor White
Write-Host "2. 运行 .\scripts\start_powershell.ps1 启动应用" -ForegroundColor White
Write-Host "3. 访问 http://localhost:5173 查看应用" -ForegroundColor White
Write-Host ""
Write-Host "🔧 其他脚本：" -ForegroundColor Yellow
Write-Host "- .\scripts\start_powershell.ps1: 启动应用" -ForegroundColor White
Write-Host "- .\scripts\dev_powershell.ps1: 开发模式" -ForegroundColor White
Write-Host "- .\scripts\test_powershell.ps1: 运行测试" -ForegroundColor White
Write-Host ""
Write-Host "📚 更多信息请查看 README.md" -ForegroundColor Yellow
Write-Host ""

Read-Host "按任意键退出"