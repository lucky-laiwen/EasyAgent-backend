# EasyAgent-backend

基于 **FastAPI** 的后端服务，为 EasyAgent 提供用户认证、**带工具能力的流式智能对话**、用户间私聊与 WebSocket 推送、好友与系统消息、聊天分享等能力。数据使用 **MySQL 8** 持久化；智能对话与标题生成在 `utils/langchain_client.py` 中通过 **LangChain Agent** 实现，可调用天气、联网搜索等工具。

---

## 一、环境要求

| 项目 | 说明 |
|------|------|
| Python | 推荐 **3.11** |
| MySQL | **8.x**，并创建空库供应用使用（见下文「数据库」） |
| 可选 | [Ollama](https://ollama.com/)（若你希望完全本地化大模型，可自行改接 `ollama`；当前主流程默认见「智能对话与模型」） |
| 可选 | **MinIO**（用户头像等文件上传依赖，见 `router/user.py` 与 `start-minio-*.sh` / `start_all.sh`） |

---

## 二、使用指南

### 1. 安装依赖

在虚拟环境中执行（推荐）：

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

- 在 MySQL 中创建数据库，例如库名 `agent`。
- 修改 `database.py` 中的 `SQLALCHEMY_DATABASE_URL`（用户、密码、主机、库名等），与本地环境一致。
- 应用启动时会在 `lifespan` 中调用 `init_db()`，由 **SQLAlchemy 按模型自动建表**。若你仓库中另有手工维护的 SQL 脚本，也可导入作为补充；**表为空一般不影响主流程**。

### 3. 环境变量（智能对话）

当前 `utils/langchain_client.py` 使用与 OpenAI 兼容的 HTTP 接口调用 **智谱 GLM**（`base_url` 与 `GLM_API_KEY`）。在项目根目录创建 `.env` 并设置：

```env
GLM_API_KEY=你的API密钥
```

> **说明**：README 中早期步骤以 **Ollama 本地模型** 为例，便于无云端 Key 的演示；与当前代码默认的云端 GLM 二选一即可。若改回 Ollama，需自行调整 `langchain_client.py` 中的 LLM 构造方式，并保证与 `router/chat` 的流式接口兼容。

### 4. Ollama（可选，用于本地大模型演练）

1. 从 [Ollama 官网](https://ollama.com/) 安装后，在终端执行：
   - `ollama pull qwen3:8b`（或你选用的模型）
2. 若拉取失败，可先退出后台的 Ollama 进程后重试。
3. 使用 `ollama list` 确认模型已存在后，执行 `ollama serve` 提供本地 API。

> Windows 用户可通过 `Win + R` 输入 `cmd` 打开命令行；macOS / Linux 直接使用系统终端即可。

### 5. 启动主服务

在项目根目录：

```bash
uvicorn main:app --reload
```

启动后提供 **OpenAPI 文档**：浏览器访问 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) 可查看与调试接口。

### 6. MCP 工具服务（可选）

仓库中 `utils/server.py` 使用 **FastMCP** 暴露**天气查询**、**DuckDuckGo 联网搜索**等工具，供支持 MCP 的客户端通过 stdio 方式连接（`python server.py` 时请在 `utils` 目录下执行，以便相对路径如 `utils/city.json` 正确）。

> **与主对话的关系**：主聊天接口当前在进程内通过 `utils/langchain_tools.py` 直接注册同名能力的 LangChain 工具，**不强制**单独起 MCP 进程即可使用天气与搜索。若你使用外部 Agent 只连 MCP，再单独启动 `server.py`。

> 联网搜索依赖 DuckDuckGo 等免费接口，**结果可能不稳定或不精确**，可多次重试或缩短查询。

### 7. 一键脚本（根目录 `start_all.sh`）

`start_all.sh` 会后台启动 `uvicorn`，并在 `utils` 目录尝试启动 **MinIO**（`./start-minio-macos.sh`）。使用前请根据本机是否安装 MinIO、路径是否匹配自行调整脚本；**Windows** 可使用项目中的 `start-minio-windows.bat`（需把其中的盘符与路径改成你的环境）。

---

## 三、项目与功能概览

### 技术栈

- **Web 框架**：FastAPI、Uvicorn  
- **数据存储**：MySQL 8、SQLAlchemy  
- **认证**：JWT（`OAuth2PasswordBearer`，Token 在 `/user/token` 等接口获取）  
- **国际化**：gettext（`utils/i18n` 中间件）  
- **智能对话**：LangChain Agent + 工具（天气、网络搜索等）；大模型以 `langchain_client` 中的配置为准  
- **其他**：WebSocket 用户私聊、Redis（如依赖中有配置使用）、MCP / FastMCP、可选 MinIO 对象存储  

### 业务模块（路由前缀）

| 前缀 | 作用简述 |
|------|----------|
| `/user` | 注册/登录/Token、当前用户、资料更新、忘记密码、文件上传、用户查询等 |
| `/chat` | 创建会话、**流式对话**、会话列表/消息、改标题、删会话、取消分享等 |
| `/user_chat` | 用户间发消息、历史、未读/全部消息、**WebSocket** `/user_chat/ws/chat/{user_id}`、接受分享等 |
| `/user_friend` | 加好友、好友列表、按昵称搜索等 |
| `/system_info` | 系统消息的查询、创建、状态更新 |

流式智能回复入口：`POST /chat/stream`（需登录，逻辑见 `router/chat.py`）。

### 项目结构（简要）

- `main.py`：应用入口、CORS、i18n、注册路由、启动时 `init_db`  
- `router/`：各业务 API  
- `models/`、`schemas/`、`crud/`：ORM、Pydantic、数据库访问  
- `utils/langchain_client.py`：流式对话与标题生成（Agent + LLM）  
- `utils/langchain_tools.py`：天气、搜索等工具实现（依赖 `utils/city.json`）  
- `utils/optimizer_system_prompt.md`：Agent 系统提示词  
- `utils/connection_manager.py`：WebSocket 连接管理  
- `utils/server.py`：独立 MCP 服务（stdio）  

---

## 四、安全与生产部署提示

- `utils/utils.py` 中 **JWT `SECRET_KEY` 为示例硬编码**，生产环境务必改为环境变量或密钥管理服务中的强随机值。  
- 生产环境应关闭 `database.py` 里 `create_engine(..., echo=True)` 的详细 SQL 打印，并配置合适的连接池与 HTTPS。  
- 首次对接前端时，注意 CORS 已设为 `allow_origins=["*"]`，上线建议收紧为实际前端域名。  

---

## 五、测试客户端

仓库中 `test_client.py` 可用于简单联调，具体用法以脚本内说明为准。  

---

如有与部署环境不符的路径（Ollama、MinIO、MySQL），以你本机实际修改的 `database.py`、`.env` 和启动脚本为准。  
