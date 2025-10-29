@echo off
chcp 65001 >nul
title A股智能投顾助手 - 运行测试

echo 🧪 运行后端测试...
cd backend
call venv\Scripts\activate.bat
if exist "tests" (
    pytest -v
) else (
    echo ⚠️  后端测试目录不存在，跳过后端测试
)

echo.
echo 🧪 运行前端测试...
cd ..\frontend
if exist "test" (
    npm run test
) else (
    echo ⚠️  前端测试目录不存在，跳过前端测试
)

echo.
echo ✅ 测试完成
pause