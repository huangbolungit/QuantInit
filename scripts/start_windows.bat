@echo off
chcp 65001 >nul
title A股智能投顾助手

echo 🚀 启动A股智能投顾助手...

:: 检查环境变量配置
if not exist "backend\.env" (
    echo ❌ 后端环境变量文件不存在，请先运行 setup_windows.bat
    pause
    exit /b 1
)

:: 检查虚拟环境
if not exist "backend\venv" (
    echo ❌ Python虚拟环境不存在，请先运行 setup_windows.bat
    pause
    exit /b 1
)

:: 检查Node.js依赖
if not exist "frontend\node_modules" (
    echo ❌ 前端依赖未安装，请先运行 setup_windows.bat
    pause
    exit /b 1
)

:: 启动后端
echo 🔧 启动后端服务...
cd backend
call venv\Scripts\activate.bat
start "Backend Server" cmd /k "uvicorn main:app --reload --host 127.0.0.1 --port 8000"

:: 等待后端启动
echo ⏳ 等待后端服务启动...
timeout /t 5 /nobreak >nul

:: 启动前端
echo 🎨 启动前端服务...
cd ..\frontend
start "Frontend Server" cmd /k "npm run dev"

:: 返回根目录
cd ..

echo.
echo ✅ 服务启动完成！
echo 📱 前端地址: http://localhost:5173
echo 📊 后端API: http://localhost:8000
echo 📖 API文档: http://localhost:8000/docs
echo.
echo 💡 提示：
echo - 关闭窗口将停止对应的服务
echo - 如需完全停止，请关闭所有弹出的命令窗口
echo - 如有问题，请检查浏览器控制台和后端日志
echo.
echo 🌐 正在打开浏览器...
timeout /t 3 /nobreak >nul
start http://localhost:5173

pause