@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 若没有 .env 则从 env 复制（config 读取 .env）
if not exist ".env" if exist "env" (
    echo [run] 使用 env 作为 .env
    copy "env" ".env" >nul
)

REM 可选：使用虚拟环境（如有）
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [run] 安装依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [run] 依赖安装失败
    pause
    exit /b 1
)

echo [run] 启动服务 http://127.0.0.1:8000
echo [run] 按 Ctrl+C 停止
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
