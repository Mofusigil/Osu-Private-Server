#!/bin/bash

# 获取当前脚本所在目录
PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
FRONTEND_PID_FILE="$PROJECT_ROOT/.frontend.pid"

echo "----------------------------------------------------------------"
echo "   Osu Private Server Auto-Launcher"
echo "----------------------------------------------------------------"

# 1. 启动 Docker 容器 (后台运行)
echo "[1/2] 正在启动后端 Docker 服务..."
cd "$PROJECT_ROOT"

# 检查 Docker 是否存在
if ! command -v docker &> /dev/null; then
    echo "错误: 未找到 docker 命令。请确保已安装 Docker。"
    exit 1
fi

# 尝试启动 docker compose
# 兼容 'docker compose' (V2) 和 'docker-compose' (V1)
if docker compose version &> /dev/null; then
    echo "使用 docker compose 命令..."
    docker compose up -d
elif command -v docker-compose &> /dev/null; then
    echo "使用 docker-compose 命令..."
    docker-compose up -d
else
    echo "错误: 未找到 docker compose 或 docker-compose 命令。"
    exit 1
fi

if [ $? -eq 0 ]; then
    echo "后端服务启动成功 (后台运行)。"
else
    echo "错误: Docker 服务启动失败，请检查上面的错误信息。"
    echo "提示: 可能需要 sudo 权限，或者 Docker 服务未启动。"
    exit 1
fi

# 等待几秒钟让数据库准备好
echo "等待 3 秒让服务初始化..."
sleep 3

# 2. 启动前端 Main.go (后台运行)
echo "[2/2] 正在启动前端 (simple-guweb)..."
cd "$PROJECT_ROOT/simple-guweb"

if [ ! -f "main.go" ]; then
    echo "错误: 在 $(pwd) 下找不到 main.go 文件。"
    exit 1
fi

# 先检查是否已有前端在运行
if [ -f "$FRONTEND_PID_FILE" ]; then
    OLD_PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "前端已在运行 (PID: $OLD_PID)，先停止旧进程..."
        kill "$OLD_PID" 2>/dev/null
        sleep 1
    fi
fi

# 后台启动前端并保存 PID
echo "正在后台运行 go run main.go ..."
nohup go run main.go > "$PROJECT_ROOT/.frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"

# 等待一下检查是否启动成功
sleep 2
if kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "前端服务启动成功 (PID: $FRONTEND_PID)"
else
    echo "警告: 前端可能启动失败，请检查日志: $PROJECT_ROOT/.frontend.log"
fi

echo "----------------------------------------------------------------"
echo "所有服务已启动！"
echo ""
echo "前端: http://localhost:8000"
echo "后端: http://localhost:10000"
echo ""
echo "查看前端日志: tail -f $PROJECT_ROOT/.frontend.log"
echo "停止所有服务: ./stop.sh"
echo "----------------------------------------------------------------"
