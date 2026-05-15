#!/bin/bash

# MinIO 启动脚本
MINIO_ROOT_USER="minioadmin"
MINIO_ROOT_PASSWORD="minioadmin"
MINIO_DATA_DIR="$HOME/minio/data"
MINIO_ADDRESS=":9000"
MINIO_CONSOLE_ADDRESS=":9001"

# 创建数据目录
mkdir -p "$MINIO_DATA_DIR"

echo "🚀 启动 MinIO 服务..."
echo "   数据目录: $MINIO_DATA_DIR"
echo "   API 地址: http://localhost:9000"
echo "   控制台: http://localhost:9001"
echo "   用户名: $MINIO_ROOT_USER"
echo "   密码: $MINIO_ROOT_PASSWORD"

# 启动 MinIO
MINIO_ROOT_USER="$MINIO_ROOT_USER" \
MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD" \
minio server "$MINIO_DATA_DIR" \
    --address "$MINIO_ADDRESS" \
    --console-address "$MINIO_CONSOLE_ADDRESS"
