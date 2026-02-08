FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /srv/root

# 1. 安装系统基础依赖
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install --no-install-recommends -y \
    git curl build-essential pkg-config \
    default-libmysqlclient-dev libssl-dev libffi-dev \
    default-mysql-client redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 2. 复制配置文件 (注意：这里我们暂时不复制过期的 poetry.lock，让 poetry 重新生成，避免冲突)
COPY pyproject.toml ./

# 3. 注入清华源配置到 pyproject.toml (这比运行 poetry source add 命令更稳定)
RUN printf "\n[[tool.poetry.source]]\nname = \"tsinghua\"\nurl = \"https://pypi.tuna.tsinghua.edu.cn/simple\"\npriority = \"primary\"\n" >> pyproject.toml

# 4. 安装 poetry，生成新的 lock 文件，并导出为 requirements.txt
#    这里运行 poetry lock 会重新解析依赖，保证与 pyproject.toml 一致
RUN pip install poetry poetry-plugin-export && \
    poetry lock && \
    poetry export --format requirements.txt --output requirements.txt --without-hashes --without dev

# 5. 安装依赖 (使用 pip，速度极快)
RUN pip install -r requirements.txt

# 6. 安装额外库
RUN pip install numpy pandas pyyaml numba

# 7. 复制代码
COPY . .

ENTRYPOINT [ "scripts/start_server.sh" ]
