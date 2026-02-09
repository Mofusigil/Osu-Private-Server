#!/bin/bash

# 获取当前脚本所在目录
PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
FRONTEND_PID_FILE="$PROJECT_ROOT/.frontend.pid"

echo "----------------------------------------------------------------"
echo "   Osu Private Server Auto-Stopper"
echo "----------------------------------------------------------------"

cd "$PROJECT_ROOT"

# 1. 停止前端
echo ">>> 正在停止前端服务..."

# 方法1: 使用保存的 PID 文件
if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "终止前端进程 (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null
        sleep 1
        # 强制终止如果还在运行
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            kill -9 "$FRONTEND_PID" 2>/dev/null
        fi
        echo "前端服务已停止。"
    else
        echo "PID 文件存在但进程已不存在。"
    fi
    rm -f "$FRONTEND_PID_FILE"
else
    echo "未找到 PID 文件，尝试通过端口查找..."
fi

# 方法2: 通过端口查找并终止 (以防 PID 文件丢失)
if command -v fuser &> /dev/null; then
    fuser -k 8000/tcp 2>/dev/null && echo "已终止占用 8000 端口的进程。"
elif command -v lsof &> /dev/null; then
    PID_8000=$(lsof -ti :8000 2>/dev/null)
    if [ -n "$PID_8000" ]; then
        echo "终止占用 8000 端口的进程 (PID: $PID_8000)..."
        kill $PID_8000 2>/dev/null
    fi
fi

# 2. 停止 Docker 后端
echo ">>> 正在停止 Docker 后端服务..."

if docker compose version &> /dev/null; then
    docker compose down
elif command -v docker-compose &> /dev/null; then
    docker-compose down
else
    echo "警告: 未找到 docker compose 命令。请手动停止 Docker。"
fi

echo "----------------------------------------------------------------"
echo "所有服务已停止。"
echo "----------------------------------------------------------------"
