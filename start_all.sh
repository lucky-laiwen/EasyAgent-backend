#!/bin/bash

echo "🚀 启动所有服务..."

# uvicorn
uv run uvicorn main:app --reload &


./start-minio-macos.sh &

# 等待所有后台任务
wait