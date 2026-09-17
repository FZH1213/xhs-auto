#!/bin/bash

# 小红书自动发布系统 - 一键启动脚本

echo "======================================"
echo "  小红书自动发布系统 - 启动中..."
echo "======================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请先安装 Python3: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 首次运行，正在创建虚拟环境..."

    # 创建虚拟环境
    python3 -m venv venv

    if [ $? -ne 0 ]; then
        echo "❌ 创建虚拟环境失败"
        exit 1
    fi

    echo "✓ 虚拟环境创建成功"
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
if ! python -c "import fastapi" 2>/dev/null; then
    echo ""
    echo "📦 正在安装依赖包..."

    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

    if [ $? -ne 0 ]; then
        echo "❌ 安装依赖失败"
        exit 1
    fi

    echo "✓ 依赖安装成功"
fi

# 安装 Playwright 浏览器驱动
echo ""
echo "🌐 检查并安装 Playwright 浏览器驱动..."
python -m playwright install chromium 2>/dev/null || true

# 启动Web服务
echo ""
echo "🚀 启动 Web 服务..."
echo ""
python main.py web