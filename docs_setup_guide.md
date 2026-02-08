# Bancho.py 私服搭建踩坑与成功指南 (2026版)

这是一份基于无数次失败总结出的血泪教程，特别针对 **Windows 客户端连接 Linux 私服** 的场景。如果你想搭建一个 osu! 私服并且不用复杂的第三方登录器，请务必严格遵守以下步骤。

## 1. 核心思路

官方 osu! 客户端有两个硬性要求：
1.  **必须使用 HTTPS**：HTTP 连接会被直接拒绝。
2.  **必须信任证书**：自签名证书必须被系统信任，且域名匹配。

因此，我们的方案是：**Docker (Bancho) + Nginx (HTTPS反代) + 自签名证书 + Hosts劫持**。

---

## 2. 服务端部署 (Linux/Docker)

### 2.1 准备文件

确保你的目录结构如下：
*   `docker-compose.yml`
*   `.env`
*   `nginx.conf`
*   `openssl.cnf` (用于生成证书)

### 2.2 配置文件关键点

**`.env` 修改：**
*   `OSU_API_KEY`: 必填，去 osu 官网申请。
*   `DISALLOW_INGAME_REGISTRATION=False`: **必须开启**，否则无法注册。
*   `DISALLOW_OLD_CLIENTS=False`: 建议开启，防止客户端版本过新被拒。

**`docker-compose.yml` 修改：**
使用官方镜像 `osuakatsuki/bancho.py:latest` 以避免编译错误。加入 Nginx 服务处理 HTTPS。

```yaml
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./cert.pem:/etc/nginx/certs/cert.pem:ro
      - ./key.pem:/etc/nginx/certs/key.pem:ro
    depends_on:
      - bancho

  bancho:
    image: osuakatsuki/bancho.py:latest
    expose:
      - ${APP_PORT} # 不再直接映射端口，全走 Nginx
    # ... 其他配置不变
```

**`nginx.conf` 内容：**
```nginx
server {
    listen 80;
    listen 443 ssl;
    server_name _; # 匹配所有域名

    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://bancho:10000;
    }
}
```

### 2.3 生成完美证书 (至关重要)

普通的 `openssl` 生成的证书会被 Chrome 和 osu! 拒绝，必须包含 **SAN (Subject Alternative Name)**。

1.  **创建配置 `openssl.cnf`**：
    ```ini
    [req]
    distinguished_name = req_distinguished_name
    x509_extensions = v3_req
    prompt = no

    [req_distinguished_name]
    CN = *.ppy.sh

    [v3_req]
    keyUsage = digitalSignature, keyEncipherment
    extendedKeyUsage = serverAuth
    subjectAltName = @alt_names

    [alt_names]
    IP.1 = 192.168.206.133  # 你的服务器IP
    DNS.1 = *.ppy.sh        # 泛域名
    DNS.2 = ppy.sh
    ```

2.  **生成证书**：
    ```bash
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout key.pem -out cert.pem -config openssl.cnf -extensions v3_req
    ```

3.  **启动服务**：
    ```bash
    sudo docker compose up -d
    ```

---

## 3. 客户端配置 (Windows)

### 3.1 安装证书 (不装连不上)

1.  把服务器上的 `cert.pem` 复制到 Windows，改名为 `bancho.crt`。
2.  双击打开 -> **安装证书**。
3.  存储位置选择：**本地计算机 (Local Machine)**。
4.  证书存储选择：**受信任的根证书颁发机构 (Trusted Root Certification Authorities)**。
5.  **验证**：用浏览器访问 `https://c.ppy.sh`，如果地址栏前面的锁头没有红色叉号，说明成功。

### 3.2 修改 Hosts (劫持域名)

用管理员权限打开 `C:\Windows\System32\drivers\etc\hosts`，添加以下内容（IP换成你的）：

```text
192.168.206.133 osu.ppy.sh
192.168.206.133 c.ppy.sh
192.168.206.133 c1.ppy.sh
192.168.206.133 c2.ppy.sh
192.168.206.133 c3.ppy.sh
192.168.206.133 c4.ppy.sh
192.168.206.133 c5.ppy.sh
192.168.206.133 c6.ppy.sh
192.168.206.133 ce.ppy.sh
192.168.206.133 a.ppy.sh
192.168.206.133 i.ppy.sh
```

### 3.3 启动与注册

1.  **不需要快捷方式参数**：直接双击 `osu!.exe` 启动即可（hosts 会自动把流量导向私服）。
2.  **注册账号**：
    *   不要直接在登录框输入新账号（会报错 Incorrect credentials）。
    *   点击 **"Create an account" (创建一个账号)**。
    *   按流程走完注册，然后回来登录。

---

## 4. 常见问题排查 (Troubleshooting)

*   **浏览器显示“不安全”**：证书没装好，或者证书没包含 SAN 字段。必须重新生成。
*   **登录一直正在连接...**：Nginx 没配好 HTTPS，或者防火墙挡住了 443 端口。
*   **Incorrect credentials**：
    1.  `.env` 里 `DISALLOW_INGAME_REGISTRATION` 没改。
    2.  你没有走注册流程，直接输了名字。
    3.  `DISALLOW_OLD_CLIENTS` 默认为 True，建议改为 False。
*   **只改了 `osu.ppy.sh`**：这是没用的，游戏连的是 `c.ppy.sh`，必须全改。

**祝你的私服运营顺利！**
