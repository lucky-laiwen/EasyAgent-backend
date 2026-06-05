# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start dev server (hot reload)
uv run uvicorn main:app --reload

# Start all services (uvicorn + MinIO)
./start_all.sh

# Install dependencies
uv pip install -r requirements.txt

# Compile i18n translations after editing .po files
pybabel compile -d locales -D messages
```

No test suite is configured. Manual testing via Swagger UI at `/docs`.

## Architecture

**Layered structure**: `router/` → `crud/` → `models/`, with `schemas/` for Pydantic validation and `utils/` for shared logic.

### Request lifecycle

Every authenticated endpoint follows the same pattern:
- `Depends(get_db)` provides a SQLAlchemy session (auto-closed)
- `Depends(get_current_user)` extracts `user_id` (int) from JWT Bearer token
- All responses use `ResponseSchema.ok(data=...)` / `ResponseSchema.fail(message=...)` — never return raw dicts

### SSE streaming (`router/chat.py` → `utils/openai_client.py`)

`POST /chat/stream` is the core AI endpoint. It creates a `Message` row (sender=1, content="") as a placeholder, then returns a `StreamingResponse` with an async generator. After streaming completes, it updates the message with final content.

The streaming pipeline:
1. Build `messages_for_llm` from chat history (role mapping: sender 0→user, 1→assistant)
2. Inject RAG context if `doc_ids` provided (or auto-retrieve from global + chat-specific docs)
3. Call `chat_stream()` / `ppt_stream()` from `openai_client.py`
4. Yield SSE events, collecting content in local variables
5. On stream end (or client disconnect via `cancel_event`), persist collected content to DB

### ReAct Agent loop (`utils/openai_client.py:chat_stream`)

Manual tool-calling loop — NOT using OpenAI's built-in tool execution:
1. Send messages + tool definitions → LLM stream
2. If response contains `tool_calls`, execute them via `TOOL_MAP` in `openai_tools.py`
3. Append assistant message + tool results to `llm_messages`
4. Repeat until no more tool calls (or client disconnects)
5. Tool executions run in parallel via `asyncio.gather` in PPT mode

### PPT generation (two-phase pipeline)

Phase 1 — Outline (`ppt_outline_stream`): ReAct loop with tools → Structured Output (`response_format={"type": "json_object"}`) → Pydantic validation via `SlideOutline` model → yield `outline` event.

Phase 2 — Slides (`ppt_slide_stream`): All slides generate concurrently via `asyncio.create_task` per slide, sharing an `asyncio.Queue`. Each task streams HTML from LLM, strips code fences, replaces CDN URLs with local `/static/vendor/` paths. Results are yielded in completion order (not page order).

PPT HTML uses **Reveal.js + TailwindCSS + Lucide Icons** from `/static/vendor/`.

### RAG pipeline (`utils/rag_service.py`)

Singleton `RagService` manages ChromaDB + Ollama embeddings. Documents are processed asynchronously via `BackgroundTasks` in `router/knowledge.py` with a semaphore limiting concurrent embeddings to 2. Retrieval supports filtering by `doc_ids`. Retrieved chunks are sanitized (link stripping, length limit) before injection into LLM context.

## Key files to understand cross-cutting concerns

- `utils/utils.py` — JWT creation/verification, password hashing, `get_current_user` dependency
- `database.py` — Engine config, `get_db` dependency, `init_db()` called on app startup via lifespan
- `main.py` — Middleware stack: CORS → i18n → static cache. Router registration.
- `utils/openai_tools.py` — Tool definitions (`TOOLS` list) and dispatch map (`TOOL_MAP` dict). Add new tools here.
- `utils/document_parser.py` — File validation rules, text extraction per format, `image_to_base64` for multimodal

## External services (all required for full functionality)

| Service | Config location | Notes |
|---------|----------------|-------|
| MySQL | `database.py` | Hardcoded connection string, auto-creates tables on startup |
| MinIO | `router/user.py`, `router/chat.py` | Hardcoded credentials, bucket `easy-agent` |
| Ollama | `utils/rag_service.py` | Model `qwen3-embedding:8b` for RAG embeddings |
| Mimo API | `utils/openai_client.py` | `MIMO_API_KEY` env var, base URL `https://token-plan-sgp.xiaomimimo.com/v1` |

## Conventions

- **No Alembic**: Schema changes via manual SQL (`sql.txt`) or direct model edits + `create_all`
- **Chinese language**: Comments, UI messages, and commit messages are in Chinese
- **i18n**: Use `request.state._("key")` for translated strings (gettext, `locales/`)
- **Message types**: `message_type` field on Message model distinguishes `"text"` vs `"ppt"` — PPT data stored as `ToolCall` with `tool_name="ppt"` or `"ppt_outline"`
- **ToolCall status**: 0=failed, 1=success, 2=in-progress (used for PPT outline editing flow)
- **File uploads**: Two separate upload paths — `router/user.py` for user files, `router/chat.py` for chat attachments (with text extraction + DB record)
