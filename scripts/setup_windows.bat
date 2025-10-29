@echo off
chcp 65001 >nul
echo 🚀 开始设置A股智能投顾助手开发环境 (Windows 10)...

:: 检查Python版本
echo 📋 检查Python版本...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装，请先安装Python 3.9或更高版本
    echo 📥 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python版本: %PYTHON_VERSION%

:: 检查Node.js版本
echo 📋 检查Node.js版本...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js未安装，请先安装Node.js 16或更高版本
    echo 📥 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✅ Node.js版本: %NODE_VERSION%

:: 设置后端环境
echo 🔧 设置后端环境...
cd backend

:: 创建虚拟环境
if not exist "venv" (
    echo 📦 创建Python虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境
echo 🔄 激活虚拟环境...
call venv\Scripts\activate.bat

:: 升级pip
echo ⬆️ 升级pip...
python -m pip install --upgrade pip

:: 安装依赖
echo 📦 安装Python依赖...
pip install -r requirements.txt

:: 创建环境变量文件
if not exist ".env" (
    echo 📝 创建环境变量文件...
    copy .env.example .env
    echo ⚠️  请编辑 backend\.env 文件，配置您的API密钥
)

:: 创建数据目录
if not exist "data" mkdir data
if not exist "data\database" mkdir data\database
if not exist "logs" mkdir logs

:: 返回根目录
cd ..

:: 设置前端环境
echo 🔧 设置前端环境...
cd frontend

:: 安装依赖
echo 📦 安装Node.js依赖...
npm install

:: 创建环境变量文件
if not exist ".env" (
    echo 📝 创建前端环境变量文件...
    (
        echo VITE_API_BASE_URL=http://localhost:8000
        echo VITE_WS_URL=ws://localhost:8000
        echo VITE_APP_TITLE=A股智能投顾助手
        echo VITE_APP_VERSION=0.2.0-MVP
    ) > .env
)

:: 返回根目录
cd ..

echo.
echo 🎉 环境设置完成！
echo.
echo 📋 下一步操作：
echo 1. 编辑 backend\.env 文件，配置您的GLM-4.6 API密钥
echo 2. 双击 start_windows.bat 启动应用
echo 3. 访问 http://localhost:5173 查看应用
echo.
echo 🔧 其他脚本：
echo - start_windows.bat: 启动应用
echo - dev_windows.bat: 开发模式
echo - test_windows.bat: 运行测试
echo.
echo 📚 更多信息请查看 README.md
echo.
pause