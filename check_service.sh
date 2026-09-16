#!/bin/bash

# 检查服务状态脚本

echo "======================================"
echo "  检查Web服务状态"
echo "======================================"
echo ""

# 检查端口是否被占用
echo "1. 检查端口8000..."
if lsof -i :8000 > /dev/null 2>&1; then
    echo "   ✓ 端口8000已被占用"
    lsof -i :8000
else
    echo "   ✗ 端口8000未被占用，服务可能未启动"
fi

echo ""

# 检查进程
echo "2. 检查Python进程..."
if pgrep -f "main.py web" > /dev/null; then
    echo "   ✓ 找到运行中的进程"
    pgrep -af "main.py web"
else
    echo "   ✗ 未找到运行中的进程"
fi

echo ""

# 测试API
echo "3. 测试API连接..."
if command -v curl > /dev/null; then
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "   ✓ API连接正常 (状态码: $response)"
    else
        echo "   ✗ API返回状态码: $response"
    fi
else
    echo "   ⚠️ curl未安装，跳过测试"
fi

echo ""
echo "======================================"
echo ""

# 如果服务未运行，提示启动
if ! lsof -i :8000 > /dev/null 2>&1; then
    echo "💡 服务未启动，运行以下命令启动:"
    echo "   ./start.sh"
    echo ""
fi