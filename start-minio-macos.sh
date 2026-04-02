#!/bin/bash

# 进入 minio 可执行文件目录（如果你是全局安装可以不写）
# cd /usr/local/bin

# 设置账号密码（强烈建议）
export MINIO_ROOT_USER=admin
export MINIO_ROOT_PASSWORD=12345678

# 启动 MinIO
minio server --console-address :9001 ~/data