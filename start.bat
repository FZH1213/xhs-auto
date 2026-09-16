@echo off
REM 小红书自动发布系统 - Windows一键启动脚本

echo ======================================
echo   小红书自动发布系统 - 启动中...
echo ======================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✓ Python 已安装

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查虚拟环境
if not exist "venv" (
    echo.
    echo 📦 首次运行，正在创建虚拟环境...

    python -m venv venv

    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )

    echo ✓ 虚拟环境创建成功
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查依赖
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo.
    echo 📦 正在安装依赖包...

    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

    if errorlevel 1 (
        echo ❌ 安装依赖失败
        pause
        exit /b 1
    )

    echo ✓ 依赖安装成功
)

REM 启动Web服务
echo.
echo 🚀 启动 Web 服务...
echo.
python main.py web

pause