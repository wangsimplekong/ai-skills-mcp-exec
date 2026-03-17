# evangelion-skills 启动脚本 (PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 若没有 .env 则从 env 复制（config 读取 .env）
if (-not (Test-Path ".env") -and (Test-Path "env")) {
    Write-Host "[run] 使用 env 作为 .env"
    Copy-Item "env" ".env"
}

# 可选：使用虚拟环境（如有）
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

Write-Host "[run] 安装依赖..."
pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "[run] 依赖安装失败"
    exit 1
}

Write-Host "[run] 启动服务 http://127.0.0.1:8000"
Write-Host "[run] 按 Ctrl+C 停止"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
