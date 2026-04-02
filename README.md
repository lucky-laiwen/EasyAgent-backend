# EasyAgent-backend

### 一、使用指南

- 首先安装本项目所使用的Python库

  推荐python版本为3.11，在总目录终端下执行`pip -m install requirements.txt`即可开始下载包依赖

  > 推荐在项目中开启python虚拟环境，避免全局环境污染，详细步骤可询问AI

- 下载ollama，推荐去官网下载 [ollama官网](https://ollama.com/)，下载完成后退回主界面，同时按Ctrl+R，输入cmd打开命令行：
  1. 输入 `ollama pull qwen3:8b`下载通义千问3的8b模型，

     > 如果遇到报错，请将后台的ollama关闭，再重新执行命令

  2. 下载完成后，可执行 `ollama list` 检查模型是否下载成功，出现对应模型后点击右下角任务控制台关闭ollama，接下来输入`ollama serve`启动大模型

  3. 使用PyCharm或VsCode等IDEA工具打开项目，打开对应的终端，输入项目启动命令

     `uvicorn main:app --reload`

     接下来另外打开一个终端，执行 `cd utils`进入utils文件夹下，接下来执行 `python server.py`用于启动MCP工具

     > MCP工具 具体包括天气查询和联网搜索，联网搜索为DuckDuckGo的免费联网搜索API，搜索内容并不准确，请多次尝试

- 将文件夹下所属的SQL文件复制进本地的MySQL 8中，供项目使用，

  > 表中数据为空并不妨碍程序运行，只需按照程序操作进行即可

### 二、介绍项目

1. 后端技术栈为：
   - Web框架：Fastapi
   - 数据存储：MySQL 8
   - 国际化：gettext
   - 大模型部署：ollama
