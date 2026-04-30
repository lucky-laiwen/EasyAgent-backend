#!/bin/bash

echo "🚀 启动所有服务..."

# uvicorn
uvicorn main:app --reload &

# utils 服务
cd utils
# MinIO
./start-minio-macos.sh &

# 等待所有后台任务
wait