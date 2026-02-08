#!/bin/bash

# 获取当前脚本所在目录
PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)

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

# 2. 启动前端 Main.go
echo "[2/2] 正在启动前端 (simple-guweb)..."
cd "$PROJECT_ROOT/simple-guweb"

if [ ! -f "main.go" ]; then
    echo "错误: 在 $(pwd) 下找不到 main.go 文件。"
    exit 1
fi

echo "正在运行 go run main.go ..."
echo "----------------------------------------------------------------"
echo "前端服务将运行在前台。"
echo "请访问: http://localhost:8000"
echo "按 Ctrl+C 可以停止前端。"
echo "----------------------------------------------------------------"

# 运行 Go 程序
go run main.go
