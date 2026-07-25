@echo off
chcp 65001 >nul
echo 正在重启后端服务...

:: 杀掉所有 uvicorn 进程
taskkill /f /im uvicorn.exe 2>nul

:: 等端口释放
timeout /t 2 /nobreak >nul

:: 重新启动
start "Agent Platform API" cmd /c "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 等待就绪
:wait
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 goto wait

echo 后端已重启就绪。
