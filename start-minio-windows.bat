@echo off

cd /d D:\xlw\minio\bin

set MINIO_ROOT_USER=admin
set MINIO_ROOT_PASSWORD=12345678

minio.exe server --address 127.0.0.1:9000 --console-address 127.0.0.1:9001 D:\xlw\minio\data