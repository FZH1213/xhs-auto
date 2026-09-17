#!/bin/bash

echo "============================================================"
echo "  小红书自动发布系统 - 重启服务"
echo "============================================================"
echo ""

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ 虚拟环境已激活"
else
    echo "✗ 虚拟环境不存在，请先运行 ./start.sh"
    exit 1
fi

# 停止旧服务
echo ""
echo "正在停止旧服务..."
pkill -f "python.*main.py web" 2>/dev/null || true
sleep 2
echo "✓ 旧服务已停止"

# 清理浏览器状态缓存（可选）
echo ""
read -p "是否清除浏览器登录状态缓存？(y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf data/browser_state 2>/dev/null || true
    echo "✓ 浏览器状态已清除，需要重新登录"
fi

# 启动新服务
echo ""
echo "============================================================"
echo "  启动新的服务..."
echo "============================================================"
echo ""
python main.py web