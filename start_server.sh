#!/bin/bash

# Skills Arena 生产级服务器启动脚本

set -e

echo "========================================="
echo "Skills Arena 生产级服务器"
echo "========================================="
echo ""

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.7+"
    exit 1
fi

echo "✅ Python 版本检查通过"
echo ""

# 检查是否在正确的目录
if [ ! -f "SKILL.md" ]; then
    echo "❌ 错误: 请在 skills-arena 目录下运行此脚本"
    echo "当前目录: $(pwd)"
    exit 1
fi

echo "✅ 目录检查通过"
echo ""

# 进入脚本目录
cd scripts

# 检查 Flask 是否安装
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  未检测到 Flask，正在安装..."
    pip3 install flask requests
    echo "✅ 依赖安装完成"
    echo ""
fi

# 检查是否存在数据目录
if [ ! -d "../data" ]; then
    echo "⚠️  数据目录不存在，正在初始化演示数据..."
    python3 init_demo.py
    echo "✅ 演示数据初始化完成"
    echo ""
fi

# 检查是否存在上传目录
if [ ! -d "../data/uploads" ]; then
    echo "⚠️  上传目录不存在，正在创建..."
    mkdir -p ../data/uploads
    echo "✅ 上传目录创建完成"
    echo ""
fi

echo "========================================="
echo "启动生产级 Web 服务器..."
echo "========================================="
echo ""
echo "服务器将在以下地址启动:"
echo "  - 主页: http://localhost:5000"
echo "  - API: http://localhost:5000/api"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动服务器
python3 production_web_server.py
