# EasyAgent-backend

### 一、使用指南

- 首先安装本项目所使用的Python库，具体如下

  aiohappyeyeballs==2.6.1
  aiohttp==3.13.2
  aiosignal==1.4.0
  annotated-types==0.7.0
  anyio==4.10.0
  attrs==25.4.0
  Authlib==1.6.5
  babel==2.17.0
  bcrypt==4.3.0
  beautifulsoup4==4.14.2
  cachetools==6.2.1
  certifi==2025.8.3
  cffi==2.0.0
  charset-normalizer==3.4.3
  click==8.2.1
  colorama==0.4.6
  cryptography==46.0.3
  cyclopts==4.0.0
  dnspython==2.7.0
  docstring_parser==0.17.0
  docutils==0.22.2
  duckduckgo_search==8.1.1
  ecdsa==0.19.1
  email_validator==2.2.0
  exceptiongroup==1.3.0
  fastapi==0.116.1
  fastapi-cli==0.0.8
  fastapi-cloud-cli==0.1.5
  fastmcp==2.12.5
  frozenlist==1.8.0
  gitdb==4.0.12
  GitPython==3.1.45
  greenlet==3.2.4
  gritql==0.2.0
  h11==0.16.0
  httpcore==1.0.9
  httptools==0.6.4
  httpx==0.28.1
  httpx-sse==0.4.3
  idna==3.10
  isodate==0.7.2
  Jinja2==3.1.6
  jsonpatch==1.33
  jsonpointer==3.0.0
  jsonschema==4.25.1
  jsonschema-path==0.3.4
  jsonschema-specifications==2025.9.1
  langchain==0.3.27
  langchain-cli==0.0.37
  langchain-core==0.3.79
  langchain-ollama==0.3.10
  langchain-text-splitters==0.3.11
  langgraph==0.6.10
  langgraph-checkpoint==2.1.2
  langgraph-prebuilt==0.6.4
  langgraph-sdk==0.2.9
  langserve==0.3.2
  langsmith==0.4.37
  lazy-object-proxy==1.12.0
  lxml==6.0.2
  markdown-it-py==4.0.0
  MarkupSafe==3.0.2
  mcp==1.16.0
  mdurl==0.1.2
  more-itertools==10.8.0
  multidict==6.7.0
  mysql-connector-python==9.4.0
  ollama==0.6.0
  openapi-core==0.19.5
  openapi-pydantic==0.5.1
  openapi-schema-validator==0.6.3
  openapi-spec-validator==0.7.2
  orjson==3.11.3
  ormsgpack==1.11.0
  packaging==25.0
  parse==1.20.2
  passlib==1.7.4
  pathable==0.4.4
  polib==1.2.0
  primp==0.15.0
  propcache==0.4.1
  pyasn1==0.6.1
  pycparser==2.23
  pydantic==2.11.7
  pydantic-settings==2.11.0
  pydantic_core==2.33.2
  Pygments==2.19.2
  PyJWT==2.10.1
  pyperclip==1.11.0
  python-dotenv==1.1.1
  python-jose==3.5.0
  python-multipart==0.0.20
  pywin32==311
  PyYAML==6.0.2
  redis==6.4.0
  referencing==0.36.2
  requests==2.32.5
  requests-toolbelt==1.0.0
  responses==0.24.1
  rfc3339-validator==0.1.4
  rich==14.1.0
  rich-rst==1.3.2
  rich-toolkit==0.15.0
  rignore==0.6.4
  rpds-py==0.27.1
  rsa==4.9.1
  sentry-sdk==2.35.0
  shellingham==1.5.4
  six==1.17.0
  smmap==5.0.2
  sniffio==1.3.1
  soupsieve==2.8
  SQLAlchemy==2.0.43
  sse-starlette==1.8.2
  starlette==0.47.3
  tenacity==9.1.2
  tomlkit==0.13.3
  typer==0.16.1
  typing-inspection==0.4.1
  typing_extensions==4.14.1
  urllib3==2.5.0
  uv==0.9.4
  uvicorn==0.35.0
  watchfiles==1.1.0
  websockets==15.0.1
  Werkzeug==3.1.1
  xxhash==3.6.0
  yarl==1.22.0
  zai-sdk==0.0.4.1
  zstandard==0.25.0

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
