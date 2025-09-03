#!/bin/bash

# FastAPI应用启动脚本

echo "🚀 启动FastAPI孕产智能问答系统..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查是否在项目根目录
if [ ! -f "requirements.txt" ]; then
    echo "❌ 请在项目根目录下运行此脚本"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖包..."
pip install -r requirements.txt

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 启动模式选择
case "$1" in
    "api")
        echo "🔌 启动API服务..."
        cd backend/fastapi_app
        python -m uvicorn main:app --host 0.0.0.0 --port 8801 --reload
        ;;
    "web")
        echo "🌐 启动Web服务..."
        cd backend/fastapi_app
        python -m uvicorn web_app:app --host 0.0.0.0 --port 8801 --reload
        ;;
    "complete")
        echo "🎯 启动完整服务..."
        cd backend/fastapi_app
        python -m uvicorn complete_app:app --host 0.0.0.0 --port 8801 --reload
        ;;
    *)
        echo "🎯 默认启动完整服务..."
        cd backend/fastapi_app
        python -m uvicorn complete_app:app --host 0.0.0.0 --port 8801 --reload
        ;;
esac