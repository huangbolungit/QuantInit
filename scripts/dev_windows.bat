@echo off
chcp 65001 >nul
title A股智能投顾助手 - 开发模式

echo 🔧 启动开发模式...

:: 启动后端开发服务器
echo 📊 启动后端开发服务器...
cd backend
call venv\Scripts\activate.bat
uvicorn main:app --reload --host 127.0.0.1 --port 8000

pause