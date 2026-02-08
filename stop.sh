#!/bin/bash

# 获取当前脚本所在目录
PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)

echo "----------------------------------------------------------------"
echo "   Osu Private Server Auto-Stopper"
echo "----------------------------------------------------------------"

cd "$PROJECT_ROOT"

echo ">>> 正在停止 Docker 后端服务..."

if docker compose version &> /dev/null; then
    docker compose down
elif command -v docker-compose &> /dev/null; then
    docker-compose down
else
    echo "警告: 未找到 docker compose 命令。请手动停止 Docker。"
    exit 1
fi

echo "----------------------------------------------------------------"
echo "后端服务已停止。"
echo "请手动按 Ctrl+C 关闭正在运行的前端 (如果还在运行)。"
echo "----------------------------------------------------------------"
