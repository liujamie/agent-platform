@echo off
chcp 65001 >nul
echo ========================================
echo  Agent Platform — 开发服务器启动脚本
echo ========================================

:: 检查虚拟环境
if exist "..\.venv\Scripts\activate" (
    call ..\.venv\Scripts\activate
) else if exist "..\venv\Scripts\activate" (
    call ..\venv\Scripts\activate
)

:: 启动后端
echo [1/2] 启动后端服务 (uvicorn)...
start "Agent Platform API" cmd /c "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 等待后端就绪
echo   Waiting for API...
:wait_api
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 goto wait_api
echo   API 已就绪

:: 启动前端
echo [2/2] 启动前端开发服务器...
cd ..\frontend
start "Agent Platform UI" cmd /c "npm run dev"

echo.
echo  API:   http://localhost:8000
echo  UI:    http://localhost:3000
echo  Docs:  http://localhost:8000/docs
echo.
