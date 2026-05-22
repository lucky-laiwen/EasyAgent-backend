# EasyAgent-backend

基于 **FastAPI** 的后端服务，为 EasyAgent 提供 **用户认证 / 带工具能力的流式智能对话 / 用户间私聊（WebSocket） / 好友与系统消息 / 聊天分享 / 文件上传 / 知识库 RAG** 等能力。

- 大模型对话：`utils/openai_client.py` 通过 **OpenAI SDK** 接入 OpenAI 兼容协议的模型（默认 **mimo-v2.5-pro**），支持流式回复、工具调用（天气、联网搜索）。
- PPT 生成：`/chat/stream` 支持 `mode="ppt"` 模式，两阶段流式生成（大纲 → 逐页 HTML），输出基于 Reveal.js + TailwindCSS 的演示文稿。
- 知识库 RAG：上传文档（PDF/Word/代码/图片等），自动分块、向量化存储至 **ChromaDB**，对话时检索相关上下文增强回复质量。
- 聊天附件：支持在对话中上传文件附件（文本/图片），文本内容自动解析，图片支持多模态输入。
- 数据持久化：**MySQL 8 + SQLAlchemy**，启动时自动建表（也可使用 `sql.txt` 中的 DDL）。
- 文件存储：**MinIO**（用户头像、附件等）。
- 实时通信：**WebSocket**（私聊、好友请求、消息已读、聊天分享）。
- 国际化：基于 `gettext` 的中英文消息文案（`locales/`）。
- 可选：**FastMCP** 独立工具服务（stdio），供外部 Agent 通过 MCP 协议调用。

---

## 一、技术栈

| 类别 | 选型 |
|------|------|
| Web 框架 | FastAPI、Uvicorn、Starlette |
| 数据库 | MySQL 8、SQLAlchemy 2.x、`mysql-connector-python` |
| 认证 | JWT（`PyJWT`）、`passlib[bcrypt]`、`OAuth2PasswordBearer` |
| 大模型 | `openai` SDK，默认接入 **mimo-v2.5-pro**（OpenAI 兼容），支持 PPT 生成 |
| Agent 工具 | 天气查询（`t.weather.sojson.com`）、联网搜索（`ddgs` / DuckDuckGo） |
| 知识库 RAG | `chromadb`（向量数据库）、`langchain-text-splitters`（文本分块）、`langchain-ollama`（Ollama 嵌入模型，默认 `qwen3-embedding:8b`） |
| 文档解析 | `python-docx`（Word）、`PyPDF2`（PDF）、内置 txt/md/csv/json/代码解析 |
| PPT 前端依赖 | TailwindCSS、Lucide Icons、Reveal.js（本地 `/static/vendor/`） |
| 对象存储 | MinIO（`minio` Python SDK） |
| 实时通信 | WebSocket（`websockets`） |
| 国际化 | `gettext`（`locales/zh`、`locales/en`） |
| 可选 MCP | `fastmcp`（`utils/server.py`，stdio 模式） |
| 其它 | `python-dotenv`、`aiohttp`、`Pydantic v2`、`redis`（依赖中包含，可按需启用） |

---

## 二、环境要求

| 组件 | 说明 |
|------|------|
| Python | 推荐 **3.11**（与 `requirements.txt` 中的依赖兼容） |
| MySQL | **8.x**，需创建空库供应用使用 |
| MinIO | 上传文件接口需要本地或远程 MinIO 服务 |
| 模型 API Key | 启用智能对话需要 `GLM_API_KEY`（或对应模型的 API Key） |
| 可选：Ollama | 知识库 RAG 嵌入模型默认使用 Ollama（`qwen3-embedding:8b`），需本地运行 Ollama 服务 |
| 可选：ChromaDB | 知识库向量存储，首次使用时自动初始化本地 `chroma_data/` 目录 |

---

## 三、快速开始

### 1. 克隆并安装依赖

建议在虚拟环境（venv / conda）中执行：

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

- 在 MySQL 中创建数据库（默认库名 `agent`）。
- 修改 `database.py` 中的连接串：

```python
SQLALCHEMY_DATABASE_URL = (
    "mysql+mysqlconnector://<user>:<password>@<host>:3306/<db_name>"
)
```

- 启动应用时，`main.py` 的 `lifespan` 会调用 `init_db()`，由 SQLAlchemy 按 `models/` 中的模型 **自动建表**。
- 如需直接使用 SQL，可参考 `sql.txt` 中的完整 DDL。

### 3. 配置环境变量

在项目根目录创建 `.env`：

```env
# 模型 API Key（用于 utils/openai_client.py）
GLM_API_KEY=your_glm_api_key
```

> `openai_client.py` 已通过 `python-dotenv` 自动加载 `.env`。当前默认模型为 `mimo-v2.5-pro`，可按需替换为其它兼容 OpenAI 协议的模型/服务。

### 4. 启动 MinIO（可选，但上传接口依赖它）

`router/user.py` 中默认连接的 MinIO：

- endpoint：`127.0.0.1:9000`
- access_key：`admin`
- secret_key：`12345678`
- bucket：`easy-agent`

**macOS / Linux**：

```bash
./start-minio-macos.sh
```

**Windows**（请先把 `start-minio-windows.bat` 中的盘符与路径改为本机实际路径）：

```bat
start-minio-windows.bat
```

> 首次使用前，请进入 MinIO 控制台（默认 `http://127.0.0.1:9001`）创建名为 `easy-agent` 的 Bucket，并按需开启匿名读权限。

### 5. 启动后端服务

```bash
uvicorn main:app --reload
```

启动后访问：

- OpenAPI 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Redoc 文档：[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 6. 一键启动脚本（可选）

`start_all.sh` 会同时拉起 `uvicorn` 与 MinIO（macOS）：

```bash
./start_all.sh
```

---

## 四、项目结构

```
EasyAgent-backend/
├── main.py                       # FastAPI 入口：CORS、i18n 中间件、静态资源、路由注册、启动建表
├── database.py                   # SQLAlchemy 引擎、Session、init_db、get_db 依赖
├── requirements.txt              # 依赖列表
├── sql.txt                       # 完整 DDL（user / chat / messages / tool_calls / chat_message / chat_share / user_friend / system_message / knowledge_base / knowledge_document / chat_attachment）
├── add_message_id_column.sql     # messages 表 message_id 列迁移脚本
├── start_all.sh                  # 一键启动 (uvicorn + MinIO)
├── start-minio-macos.sh          # MinIO 启动脚本（macOS）
├── start-minio-windows.bat       # MinIO 启动脚本（Windows）
├── babel.cfg                     # i18n 提取配置
├── test_client.py                # MCP & DDG 调用样例脚本
│
├── router/                       # 业务 API 路由
│   ├── user.py                   # /user：注册/登录/Token、当前用户、文件上传等
│   ├── chat.py                   # /chat：创建会话、流式对话（文本/PPT）、消息/列表、改标题、删会话、附件上传
│   ├── knowledge.py              # /knowledge：知识库文档管理（上传/查询/删除/重试）
│   ├── user_chat.py              # /user_chat：私聊 REST + WebSocket、聊天分享
│   ├── user_friend.py            # /user_friend：加好友、好友列表、搜索
│   └── system_message.py         # /system_info：系统消息查询/创建/状态更新
│
├── models/                       # SQLAlchemy ORM 模型
│   ├── user.py                   # User
│   ├── chat.py                   # Chat（含 kb_id 知识库绑定）
│   ├── messages.py               # Message（AI 会话消息，含 message_type: text/ppt、rag_references）
│   ├── tool_call.py              # ToolCall（工具调用记录）
│   ├── chat_attachment.py        # ChatAttachment（聊天附件）
│   ├── chat_message.py           # ChatMessage（用户间私聊消息）
│   ├── chat_share.py             # ChatShare（聊天分享）
│   ├── knowledge.py              # KnowledgeBase / KnowledgeDocument（知识库 & 文档）
│   ├── user_friend.py            # UserFriend
│   └── system_message.py         # SystemMessage
│
├── schemas/                      # Pydantic v2 Schema（请求/响应）
│   ├── response.py               # 通用 ResponseSchema（ok / fail）
│   ├── knowledge.py              # 知识库相关 Schema
│   ├── user.py / chat.py / messages.py / user_chat.py / chat_share.py
│   ├── user_friend.py / system_message.py
│
├── crud/                         # 数据访问层
│   ├── knowledge.py              # 知识库 & 文档 CRUD
│   ├── chat_attachment.py        # 聊天附件 CRUD
│   ├── user.py / chat.py / messages.py / user_chat.py
│   ├── chat_share.py / user_friend.py / system_message.py
│
├── utils/
│   ├── openai_client.py          # 流式对话、PPT 生成、标题生成（OpenAI SDK）
│   ├── rag_service.py            # RAG 服务：ChromaDB 向量存储 + Ollama 嵌入 + 检索
│   ├── document_parser.py        # 多格式文档解析（txt/md/csv/json/py/js/docx/pdf）
│   ├── optimizer_system_prompt.md# Agent 系统提示词（输出规范、工具触发规则）
│   ├── ppt_outline_prompt.md     # PPT 大纲生成提示词
│   ├── ppt_slide_prompt.md       # PPT 单页 HTML 生成提示词
│   ├── ppt_system_prompt.md      # PPT 系统提示词
│   ├── server.py                 # 独立 MCP 服务（FastMCP，stdio）
│   ├── connection_manager.py     # WebSocket 连接管理器（按 user_id 维护）
│   ├── i18n.py                   # gettext 中间件
│   ├── utils.py                  # JWT、密码哈希、当前用户依赖
│   ├── ollama_client.py          # （可选）Ollama 客户端实现
│   ├── city.json                 # 天气工具的城市编码表
│   └── test.py
│
├── static/                       # 静态资源（浏览器长期缓存）
│   └── vendor/                   # PPT 前端依赖
│       ├── tailwind.js           #   TailwindCSS Play CDN
│       ├── lucide.min.js         #   Lucide Icons 0.344.0
│       ├── reveal.js             #   Reveal.js 4.6.1
│       ├── reveal.css            #   Reveal.js 核心样式
│       ├── reveal-reset.css      #   Reveal.js reset 样式
│       └── reveal-white.css      #   Reveal.js white 主题
│
├── chroma_data/                  # ChromaDB 本地向量数据库（已 .gitignore）
│
├── docs/                         # 文档
│   └── ppt-frontend-integration.md # PPT 前端适配说明
│
└── locales/                      # i18n 翻译文件
    ├── zh/LC_MESSAGES/
    └── en/LC_MESSAGES/
```

---

## 五、API 概览

> 所有需要登录的接口都通过 `Depends(get_current_user)` 解析 `Authorization: Bearer <JWT>`。

### 1. `/user`（用户与文件）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/user/create_user` | 注册（返回用户信息 + JWT） |
| POST | `/user/login` | 邮箱 + 密码登录 |
| POST | `/user/token` | OAuth2 表单登录（用于 Swagger UI） |
| GET | `/user/current_user` | 获取当前登录用户 |
| PUT | `/user/update_user` | 更新昵称 / 邮箱 / 头像 |
| POST | `/user/forget_password` | 重置密码 |
| DELETE | `/user/logout` | 注销当前账号（删除用户） |
| GET | `/user/get_user/{user_id}` | 按 ID 获取用户 |
| GET | `/user/query_All` | 查询全部用户 |
| POST | `/user/upload_file` | 上传文件至 MinIO，返回带签名的访问 URL |

### 2. `/chat`（AI 对话）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat/create_chat` | 创建新会话（自动生成标题） |
| POST | `/chat/stream` | **流式 AI 对话**（SSE，支持 `mode="ppt"` 生成演示文稿，支持 `doc_ids` 知识库检索 + `file_ids` 附件输入） |
| POST | `/chat/upload_file` | 上传聊天附件（文本/图片），自动解析文本内容 |
| GET | `/chat/get_chat_list` | 分页获取当前用户的会话列表 |
| GET | `/chat/get_chat_message/{chat_id}` | 获取指定会话的消息 |
| POST | `/chat/update_chat_title` | 更新会话标题 |
| DELETE | `/chat/delete_chat/{chat_id}` | 删除会话 |
| GET | `/chat/cancel_share/{share_id}` | 被分享方取消分享 |

### 3. `/user_chat`（用户间私聊）

| 方法 | 路径 | 说明 |
|------|------|------|
| WS | `/user_chat/ws/chat/{user_id}` | 私聊 WebSocket（详见下文） |
| POST | `/user_chat/send_message` | REST 方式发送私聊消息 |
| GET | `/user_chat/get_chat_history/{receiver_id}` | 与某用户的历史消息（含分享聊天） |
| GET | `/user_chat/get_unread_messages` | 我的未读消息 |
| GET | `/user_chat/get_all_messages` | 我接收到的全部消息 |
| GET | `/user_chat/accept_share/{share_id}` | 接受聊天分享 |

### 4. `/user_friend`（好友）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/user_friend/add_friend` | 添加好友 |
| GET | `/user_friend/get_friend_list` | 我的好友列表 |
| GET | `/user_friend/search_friend` | 按昵称搜索（区分已是好友 / 待确认 / 非好友） |

### 5. `/system_info`（系统消息）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/system_info/get_system_messages` | 当前用户的系统消息 |
| POST | `/system_info/create_system_message` | 创建系统消息 |
| POST | `/system_info/update_system_message_status` | 更新系统消息状态 |

### 6. `/knowledge`（知识库 & RAG）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/knowledge/upload_doc` | 上传文档到全局知识库（自动分块、向量化），支持 PDF/Word/代码/图片等 |
| GET | `/knowledge/get_doc_list` | 获取全局知识库的文档列表 |
| GET | `/knowledge/get_chat_doc_list/{chat_id}` | 获取会话专属文档列表 |
| DELETE | `/knowledge/delete_doc/{doc_id}` | 删除文档（同时清除向量数据） |
| GET | `/knowledge/get_doc_content/{doc_id}` | 获取文档分块内容 |
| POST | `/knowledge/retry_doc/{doc_id}` | 重试失败的文档处理 |

---

## 六、流式对话协议（SSE）

`POST /chat/stream` 返回 `text/event-stream`，前端可用 `EventSource` 或自行解析 `data:` 行。

### 文本模式（默认）

```json
{
  "id": 123,
  "message": "明天上海天气如何？",
  "doc_ids": [1, 2],
  "file_ids": [10]
}
```

事件流：

```
data: {"type": "think", "content": "..."}\n\n
data: {"type": "text",  "content": "..."}\n\n
data: {"type": "tool_name", "tool_name": "weather_query"}\n\n
data: {"type": "tool_content", "tool_content": {...}}\n\n
data: {"references": [{"doc_id": 1, "filename": "doc.pdf", "chunk_index": 0, "snippet": "..."}]}\n\n
event: done
data: {"done": true}
```

### PPT 模式

```json
{
  "id": 123,
  "message": "做一个关于人工智能发展的PPT",
  "mode": "ppt"
}
```

两阶段流式生成：阶段 1 生成大纲（含样式），阶段 2 逐页生成完整 HTML。事件流：

```
data: {"type": "think", "content": "..."}\n\n           // 思考过程（如有）
data: {"type": "text", "content": "..."}\n\n            // 前导文本
data: {"type": "outline", "slides": [...], "style": {...}}\n\n  // 大纲 + 样式
data: {"type": "slide_start", "index": 0}\n\n           // 开始生成第 N 页
data: {"type": "slide_chunk", "index": 0, "content": "<html>..."}\n\n  // HTML 增量
data: {"type": "slide_end", "index": 0}\n\n             // 第 N 页完成
...（重复 slide_start/chunk/end）
data: {"type": "text", "content": "已生成 N 页"}\n\n     // 结束语
event: done
data: {"done": true}
```

PPT 的 HTML 基于 **Reveal.js + TailwindCSS + Lucide Icons**，前端通过 `iframe srcdoc` 渲染。前端适配详见 `docs/ppt-frontend-integration.md`。

### 事件类型

| 事件 | 说明 |
|------|------|
| `think` | 模型思考过程（如有） |
| `text` | 模型回复内容（增量） |
| `tool_name` | 开始调用工具 |
| `tool_content` | 工具返回结果（已 JSON 解析） |
| `outline` | PPT 大纲（含 `slides` 数组和 `style` 对象） |
| `slide_start` | 开始生成某页 |
| `slide_chunk` | 某页 HTML 增量 |
| `slide_end` | 某页生成完成 |
| `done` | 流式结束 |
| `error` | 异常时返回错误信息 |

> 服务端会先把用户消息落库，再把整段历史按 `system + user/assistant` 顺序送入模型；流结束后再把模型最终回复（含 `think_content` / `tool_name` / `tool_content`）一起落库。PPT 数据以 `tool_name="ppt"` 存入 ToolCall 表。

---

## 七、Agent 工具

`utils/openai_client.py` 中注册了两个工具，文本模式和 PPT 模式均可调用：

- **`weather_query(city)`**
  调用 `http://t.weather.sojson.com/api/weather/city/{areaid}`，配合 `utils/city.json` 做城市名归一化（自动去除「市/县/区/镇/乡/村」后缀）。返回当天天气与完整 forecast 数组。
- **`web_search(query)`**
  使用 `ddgs`（DuckDuckGo）并行抓取 `text / images / news`，每类最多 50 条。

工具的触发规则与输出格式由 `utils/optimizer_system_prompt.md` 约束（要求纯 Markdown 输出、禁用 HTML、禁用表格等）。

> **MCP 模式（可选）**：`utils/server.py` 通过 `FastMCP` 暴露同名工具。在 `utils/` 目录下执行 `python server.py` 即可启动 stdio 模式的 MCP 服务（参考 `test_client.py` 中的 `StdioTransport` 用例）。**主聊天接口不依赖 MCP 进程**，工具会直接在进程内被调用。

---

## 八、知识库 RAG

通过 `/knowledge` API 上传文档，系统自动完成 **文本提取 → 分块 → 向量化 → ChromaDB 存储**，对话时根据用户消息检索相关上下文。

### 支持的文档格式

| 格式 | 说明 |
|------|------|
| `.txt` / `.md` | 纯文本，直接提取 |
| `.csv` | 表格数据，转为文本（限前 100 行） |
| `.json` | JSON 数据，格式化输出（限 50KB） |
| `.py` / `.js` | 代码文件，直接提取 |
| `.doc` / `.docx` | Word 文档，使用 `python-docx` 提取段落 |
| `.pdf` | PDF 文件，使用 `PyPDF2` 提取文字（限 80KB） |
| `.jpg` / `.jpeg` / `.png` / `.webp` | 图片文件，转为 base64 供多模态 LLM 使用 |

### RAG 工作流程

1. 用户通过 `POST /knowledge/upload_doc` 上传文档
2. 后端异步执行：文本提取 → `RecursiveCharacterTextSplitter` 分块（300 字/块，50 字重叠）→ Ollama 嵌入 → ChromaDB 存储
3. 对话时（`POST /chat/stream`），支持两种模式：
   - **指定文档**：通过 `doc_ids` 参数选择特定文档检索
   - **自动检索**：自动搜索全局知识库 + 当前会话专属文档
4. 检索结果（默认 Top 3）作为上下文注入 LLM，回复后返回 `references` 引用信息

### 嵌入模型配置

默认使用 Ollama 本地服务的 `qwen3-embedding:8b` 模型，需在本地运行：

```bash
ollama pull qwen3-embedding:8b
```

> 如需使用其他嵌入模型，修改 `utils/rag_service.py` 中的 `embedding_model` 参数。

---

## 九、WebSocket 协议（私聊）

连接：`ws://<host>:8000/user_chat/ws/chat/{user_id}`，所有消息为 JSON。

### 客户端 -> 服务端

1. **发送私聊消息**（可附带分享某个 AI 会话）：

```json
{
  "to_user_id": 2,
  "content": "在吗？",
  "chatId": 10,           // 可选：分享的 chat.id
  "title": "天气问答"      // 可选：分享会话标题（chatId 存在时）
}
```

2. **更新消息已读状态**：

```json
{
  "messageId": 100,
  "to_user_id": 2
}
```

3. **发送好友请求**：

```json
{
  "type": "add_friend",
  "to_user_id": 2,
  "content": { "name": "Alice" }
}
```

4. **同意好友请求**：

```json
{
  "type": "accept_friend_request",
  "to_user_id": 2,
  "message_id": 5,
  "title": "好友请求",
  "content": "已同意",
  "action_type": 1
}
```

### 服务端 -> 客户端

服务端会向收发双方推送消息字典，并附带 `type` 字段（如 `update_message_status` / `add_friend` / `accept_friend_request`）。`datetime` 字段统一序列化为 ISO 字符串。

---

## 十、数据库模型一览

详见 `sql.txt` 与 `models/`：

- `user`：用户基础信息（含头像默认值、注册时间）
- `chat`：AI 会话（标题、所属用户、时间、`kb_id` 知识库绑定）
- `messages`：AI 会话消息（`sender`：0=用户 / 1=AI，包含 `think_content` / `tool_content` / `tool_name`，`message_type`：text / ppt，`rag_references` 知识库引用）
- `tool_calls`：工具调用记录（`tool_name` / `tool_content` / `tool_input` / `status`）
- `chat_attachment`：聊天附件（文件名、类型、大小、MinIO key、文本内容）
- `chat_message`：用户间私聊消息（含 `share_chat_id`、`status` 已读状态）
- `chat_share`：聊天分享（owner / shared_to / 权限）
- `user_friend`：好友关系（`status`：0=待确认 / 1=已确认 / 2=被拉黑）
- `system_message`：系统消息（含 `action_type`、来源用户）
- `knowledge_base`：知识库（名称、描述、ChromaDB collection 名称）
- `knowledge_document`：知识库文档（文件名、类型、分块数、处理状态、`chat_id` / `message_id` 绑定）

---

## 十一、国际化（i18n）

- 中间件：`utils/i18n.py`，根据请求头 `Accept-Language` 自动加载对应翻译。
- 文案目录：`locales/zh/LC_MESSAGES/messages.po`、`locales/en/LC_MESSAGES/messages.po`。
- 在路由中通过 `request.state._("key")` 取得当前语言对应文案。
- 编译命令（修改 `.po` 后）：

```bash
pybabel compile -d locales -D messages
```

---

## 十二、安全与生产部署

- **JWT `SECRET_KEY` 已硬编码在 `utils/utils.py`，生产环境务必改为环境变量或密钥管理服务中的强随机值**。
- `database.py` 中 `create_engine(..., echo=True)` 会打印全部 SQL，**生产环境请关闭** 并配置合适的连接池。
- `main.py` 的 CORS 设为 `allow_origins=["*"]`，上线建议收紧为实际前端域名。
- MinIO 的 `access_key/secret_key` 硬编码于 `router/user.py` 和 `router/chat.py`，建议改为环境变量加载。
- `ACCESS_TOKEN_EXPIRE_MINUTES = 15`（注：当前实现实际乘以 `timedelta(hours=...)`，生产前请按需修正为分钟语义）。
- 静态资源（`/static/vendor/`）已配置 `Cache-Control: public, max-age=31536000, immutable`，浏览器首次加载后长期缓存。前端如与后端分开部署，需在 HTML 中注入 `<base>` 标签指向后端地址（详见 `docs/ppt-frontend-integration.md`）。
- ChromaDB 向量数据存储在 `chroma_data/` 目录，已加入 `.gitignore`，生产环境建议挂载持久化存储。

---

## 十三、调试与测试

- Swagger UI：`http://127.0.0.1:8000/docs` 可直接登录并调试所有 REST 接口。
- WebSocket：可使用浏览器扩展（如 `Browser WebSocket Client`）或 `wscat` 测试 `/user_chat/ws/chat/{user_id}`。
- `test_client.py`：演示如何通过 `FastMCP` 客户端以 stdio 方式调用 `utils/server.py` 中的工具，以及直接使用 `ddgs` 进行联网搜索。

---

## 十四、常见问题

- **联网搜索结果不稳定？**
  `ddgs` 依赖 DuckDuckGo 的免费接口，可能受网络/限流影响，建议在客户端做重试或缩短查询词。
- **`init_db()` 没有创建索引/外键？**
  `Base.metadata.create_all` 会按模型创建表与索引；如需更精细的约束，请直接执行 `sql.txt`。
- **如何切换到 Ollama 等本地模型？**
  替换 `utils/openai_client.py` 中的 `AsyncOpenAI` 客户端配置，将 `base_url` 指向 Ollama 的 OpenAI 兼容端点即可。
- **知识库 RAG 检索无效果？**
  确认 Ollama 服务已启动且 `qwen3-embedding:8b` 模型已下载；检查 `chroma_data/` 目录是否存在且有数据；确认文档状态为 `completed`。
- **文档上传后状态为 `failed`？**
  检查 Ollama 嵌入服务是否正常运行；查看服务端日志中的错误信息；可调用 `POST /knowledge/retry_doc/{doc_id}` 重试。

---

> 如部署环境与默认值不一致（数据库连接串、MinIO 地址、模型 API），请以你本机修改后的 `database.py`、`.env`、`router/user.py` 与启动脚本为准。
