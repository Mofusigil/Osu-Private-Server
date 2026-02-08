# 🎮 Osu! Private Server

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8.svg)](https://golang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

基于 [bancho.py](https://github.com/osuAkatsuki/bancho.py) 的 osu! 私服，包含自定义功能和 Go 语言前端。

## ✨ 特性

### 🎯 后端 (bancho.py)
- 完整的 osu! 服务器实现，支持所有游戏模式
- 支持 Relax (RX) 和 Autopilot (AP) 模式
- 完整的 PP 计算系统
- 多人游戏 (Multiplayer) 支持
- 好友系统和聊天功能

### ⭐ Mania Star-Rating-Rebirth
- 集成 [Star-Rating-Rebirth](https://github.com/xxmlg1783xx2/Star-Rating-Rebirth) 算法
- 提供更准确的 Mania 难度评级
- 使用 `!sr` 命令查询 Mania 谱面的 Rebirth SR

### 🌐 前端 (simple-guweb)
- 使用 Go 语言编写的轻量级 Web 前端
- 包含用户资料页、排行榜等功能
- 简洁现代的 UI 设计

## 📦 项目结构

```
.
├── app/                    # bancho.py 核心代码
├── simple-guweb/           # Go 语言前端
├── Star-Rating-Rebirth/    # Mania SR 计算算法
├── scripts/                # 启动脚本
├── docker-compose.yml      # Docker 配置
├── nginx.conf              # Nginx 配置
└── .env.example            # 环境变量示例
```

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Go 1.21+
- Docker & Docker Compose
- MySQL 8.0+
- Redis

### 部署步骤

1. **克隆仓库**
```bash
git clone https://github.com/Mofusigil/Osu-Private-Server.git
cd Osu-Private-Server
```

2. **复制配置文件**
```bash
cp .env.example .env
```

3. **编辑 `.env` 文件**
- 修改 `DOMAIN` 为你的域名
- 配置数据库凭据 (`DB_USER`, `DB_PASS`, `DB_NAME`)
- 设置 `OSU_API_KEY` (从 osu! 官网获取)
- 配置 SSL 证书路径

4. **启动服务**
```bash
./start.sh
```

5. **停止服务**
```bash
./stop.sh
```

## 🎮 游戏内命令

| 命令 | 描述 |
|------|------|
| `!help` | 显示所有可用命令 |
| `!with <acc/mods>` | 查询指定条件下的 PP |
| `!sr` | 查询 Mania 谱面的 Rebirth SR |
| `!recent` 或 `!r` | 显示最近成绩 |
| `!top <mode>` | 显示前 10 成绩 |
| `!roll` | 掷骰子 |

## 🔧 配置说明

### Nginx 反向代理
项目包含预配置的 `nginx.conf`，支持：
- HTTPS (需要配置 SSL 证书)
- 反向代理到 bancho.py 后端
- 反向代理到 simple-guweb 前端
- osu! 客户端 API 路由

### 域名配置
需要配置以下子域名指向你的服务器：
- `osu.yourdomain.com` - 主域名
- `c.yourdomain.com` - bancho 服务
- `ce.yourdomain.com` - bancho 服务 (加密)
- `a.yourdomain.com` - 头像服务
- `api.yourdomain.com` - API 服务

## 📝 开发说明

### 运行前端开发服务器
```bash
cd simple-guweb
go run main.go
```

### 代码风格
- Python: Black + isort
- Go: gofmt

## 📄 许可证

本项目基于 [MIT License](LICENSE) 许可。

## 🙏 致谢

- [bancho.py](https://github.com/osuAkatsuki/bancho.py) - Akatsuki 团队
- [Star-Rating-Rebirth](https://github.com/xxmlg1783xx2/Star-Rating-Rebirth) - Mania SR 算法
- [osu!](https://osu.ppy.sh/) - ppy

---

⭐ 如果这个项目对你有帮助，请给一个 Star！
