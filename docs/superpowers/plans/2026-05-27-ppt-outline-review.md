# PPT 大纲审核功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 PPT 生成拆分为大纲生成和 PPT 生成两个独立阶段，支持用户审核和修改大纲。

**Architecture:** 从 `ppt_stream()` 中提取大纲生成逻辑为 `ppt_outline_stream()`，提取幻灯片生成逻辑为 `ppt_slide_stream()`。新增 3 个 API 端点分别对应大纲生成、大纲更新、PPT 生成。大纲数据存入 `tool_calls` 表（`tool_name="ppt_outline"`），PPT 数据独立存储（`tool_name="ppt"`）。

**Tech Stack:** FastAPI, SQLAlchemy, OpenAI-compatible API (Mimo), SSE streaming

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `crud/messages.py` | Modify | 新增 `get_tool_call_by_message_and_name()` 查询函数 |
| `utils/openai_client.py` | Modify | 拆分 `ppt_stream()` 为 `ppt_outline_stream()` + `ppt_slide_stream()` |
| `router/chat.py` | Modify | 新增 3 个端点：`ppt_outline`、`update_outline`、`ppt_generate` |

---

### Task 1: 新增 CRUD 查询函数

**Files:**
- Modify: `crud/messages.py:93`（在文件末尾追加）

- [ ] **Step 1: 添加 `get_tool_call_by_message_and_name` 函数**

在 `crud/messages.py` 末尾追加：

```python
# 按 message_id 和 tool_name 查询工具调用记录
def get_tool_call_by_message_and_name(db: Session, message_id: int, tool_name: str) -> Optional[ToolCall]:
    return db.query(ToolCall).filter(
        ToolCall.message_id == message_id,
        ToolCall.tool_name == tool_name
    ).first()
```

- [ ] **Step 2: 验证导入无误**

Run: `cd /Users/xlw/Documents/GitHub/EasyAgent-backend && python -c "from crud.messages import get_tool_call_by_message_and_name; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add crud/messages.py
git commit -m "feat: add get_tool_call_by_message_and_name CRUD helper"
```

---

### Task 2: 拆分 `ppt_stream()` 为 `ppt_outline_stream()`

**Files:**
- Modify: `utils/openai_client.py:282-634`

- [ ] **Step 1: 在 `ppt_stream()` 函数之前添加 `ppt_outline_stream()`**

在 `utils/openai_client.py` 的 `ppt_stream` 函数（第 282 行）之前，添加以下函数：

```python
async def ppt_outline_stream(messages, cancel_event: asyncio.Event = None):
    """
    PPT 大纲生成专用流式函数：
    工具调用 ReAct 循环 + Structured Output 生成大纲 → yield outline 事件

    与 ppt_stream() 的阶段1逻辑完全一致，但不进入阶段2（HTML生成）。
    """
    user_msg = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")

    history = messages[:-1] if messages and messages[-1].get("role") == "user" else messages

    # === 生成大纲（支持工具调用）===
    outline_messages = [{"role": "system", "content": ppt_outline_prompt}]
    if history:
        recent = history[-6:]
        history_text = "\n".join(
            f"{'用户' if m.get('role') == 'user' else '助手'}：{m.get('content', '')[:500]}"
            for m in recent
        )
        outline_messages.append({
            "role": "system",
            "content": f"以下是之前的对话历史，用户可能引用其中的内容作为 PPT 主题，请结合上下文理解用户意图：\n\n{history_text}"
        })
    outline_messages.append({"role": "user", "content": user_msg})

    # ReAct 循环
    while True:
        collected_content = ""
        collected_reasoning = ""
        tool_calls_map = {}

        stream = await client.chat.completions.create(
            model="mimo-v2.5-pro",
            messages=outline_messages,
            tools=TOOLS,
            stream=True,
            extra_body={"thinking": {"type": "disabled"}},
        )

        async for chunk in stream:
            if cancel_event and cancel_event.is_set():
                await stream.close()
                return

            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                collected_reasoning += reasoning
                yield {"content": reasoning, "type": "think"}

            if delta.content is not None:
                collected_content += delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name or "",
                            "arguments": tc.function.arguments or "",
                        }
                    else:
                        if tc.id:
                            tool_calls_map[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls_map[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_map[idx]["arguments"] += tc.function.arguments

        if (cancel_event and cancel_event.is_set()) or not tool_calls_map:
            break

        assistant_msg = {"role": "assistant", "content": collected_content or None}
        if collected_reasoning:
            assistant_msg["reasoning_content"] = collected_reasoning
        assistant_msg["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            }
            for tc in tool_calls_map.values()
        ]
        outline_messages.append(assistant_msg)

        for tc in tool_calls_map.values():
            tool_name = tc["name"]
            tool_args = json.loads(tc["arguments"])

            args = tool_args.get("city") or tool_args.get("query")
            yield {"type": "tool_start", "tool": tool_name, "tool_run_id": tc["id"], "args": args}

            tool_func = TOOL_MAP.get(tool_name)
            if tool_func:
                tool_result = await tool_func(**tool_args)
            else:
                tool_result = f"未知工具: {tool_name}"

            tool_content = tool_result
            if isinstance(tool_result, str):
                try:
                    parsed = json.loads(tool_result)
                    if tool_name == "weather_query":
                        tool_content = parsed.get("full_data", parsed)
                    else:
                        tool_content = parsed
                except json.JSONDecodeError:
                    pass

            yield {"type": "tool_mid", "tool": tool_name, "tool_run_id": tc["id"], "tool_content": tool_content}

            outline_messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": tool_result}
            )

    # === 用 Structured Output 生成大纲 JSON ===
    outline_messages.append({
        "role": "user",
        "content": "请根据以上信息，严格按照 JSON Schema 输出大纲。",
    })

    resp = await client.chat.completions.create(
        model="mimo-v2.5-pro",
        messages=outline_messages,
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}},
    )

    raw = resp.choices[0].message.content or ""

    # Pydantic 校验
    try:
        outline = SlideOutline.model_validate_json(raw)
    except Exception as e:
        yield {"type": "error", "content": f"大纲结构校验失败: {str(e)}"}
        return

    if not outline.slides:
        yield {"type": "error", "content": "大纲为空，请重试"}
        return

    slides = [s.model_dump() for s in outline.slides]
    style = outline.style.model_dump()

    yield {"type": "outline", "slides": slides, "style": style}
```

- [ ] **Step 2: 验证语法正确**

Run: `cd /Users/xlw/Documents/GitHub/EasyAgent-backend && python -c "from utils.openai_client import ppt_outline_stream; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add utils/openai_client.py
git commit -m "feat: add ppt_outline_stream() for outline-only generation"
```

---

### Task 3: 添加 `ppt_slide_stream()`

**Files:**
- Modify: `utils/openai_client.py`（在 `ppt_outline_stream` 之后、`ppt_stream` 之前添加）

- [ ] **Step 1: 添加 `ppt_slide_stream()` 函数**

在 `ppt_outline_stream()` 函数之后、`ppt_stream()` 函数之前添加：

```python
async def ppt_slide_stream(slides, style, user_msg: str, cancel_event: asyncio.Event = None):
    """
    PPT 幻灯片生成专用流式函数：
    接收已确认的大纲和样式，逐页生成 HTML。

    Args:
        slides: 大纲 slides 数组（list of dict）
        style: 大纲 style 对象（dict）
        user_msg: 用户原始请求消息
        cancel_event: 客户端断开时设置此事件
    """
    style_guide = json.dumps(style, ensure_ascii=False, indent=2) if style else "{}"

    prev_html = ""
    trailing_text = ""
    failed_slides = []
    total_slides = len(slides)

    for slide_i, slide in enumerate(slides):
        index = slide.get("index", 0)
        title = slide.get("title", "")
        description = slide.get("description", "")
        layout = slide.get("layout", "content")

        yield {"type": "slide_start", "index": index}

        subtitle = slide.get("subtitle", "")
        points = slide.get("points", [])
        visual_suggestion = slide.get("visualSuggestion", "")

        points_text = "\n".join(f"  - {p}" for p in points) if points else "  (无)"

        user_content = (
            f"标题: {title}\n"
            f"副标题: {subtitle}\n"
            f"描述: {description}\n"
            f"主题: {user_msg}\n"
            f"布局类型: {layout}\n"
            f"\n--- 内容要点（必须全部体现在幻灯片中）---\n{points_text}"
        )
        if visual_suggestion:
            user_content += f"\n\n--- 视觉建议 ---\n{visual_suggestion}"
        user_content += f"\n\n--- 样式指南（必须严格遵守）---\n{style_guide}"
        if prev_html:
            style_ref = extract_style_summary(prev_html)
            user_content += f"\n\n--- 前一页视觉风格摘要（保持一致性参考）---\n{style_ref}"

        slide_messages = [
            {"role": "system", "content": ppt_slide_prompt},
            {"role": "user", "content": user_content},
        ]

        html_started = False
        html_ended = False
        buffer = ""
        full_html = ""
        trailing_text = ""

        try:
            stream = await client.chat.completions.create(
                model="mimo-v2.5-pro",
                messages=slide_messages,
                stream=True,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as e:
            failed_slides.append(index + 1)
            yield {"type": "text", "content": f"\n⚠️ 第 {index + 1} 页 API 调用失败: {str(e)[:100]}，跳过\n"}
            continue

        async for chunk in stream:
            if cancel_event and cancel_event.is_set():
                await stream.close()
                return

            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield {"content": reasoning, "type": "think"}

            if delta.content is None:
                continue

            if html_ended:
                trailing_text += delta.content
                continue

            if not html_started:
                buffer += delta.content
                lower_buf = buffer.lower()

                fence_pos = buffer.find("```")
                if fence_pos != -1:
                    after_fence = buffer[fence_pos + 3:]
                    for lang in ["html", "htm", "ht", "h"]:
                        if after_fence.lower().startswith(lang):
                            after_fence = after_fence[len(lang):]
                            break
                    buffer = after_fence
                    lower_buf = buffer.lower()

                if "<html" in lower_buf or "<!doctype" in lower_buf:
                    html_started = True
                    html_start_idx = lower_buf.find("<!doctype")
                    if html_start_idx == -1:
                        html_start_idx = lower_buf.find("<html")
                    filtered = replace_cdn_urls(buffer[html_start_idx:])
                    full_html += filtered
                    yield {"type": "slide_chunk", "index": index, "content": filtered}
            else:
                chunk_content = replace_cdn_urls(delta.content)
                if not html_ended:
                    pending_html = full_html + chunk_content
                    if "</html>" in pending_html.lower():
                        html_ended = True
                        chunk_lower = chunk_content.lower()
                        close_pos = chunk_lower.rfind("</html>")
                        if close_pos != -1:
                            end_pos = close_pos + len("</html>")
                            html_part = chunk_content[:end_pos]
                            full_html += html_part
                            yield {"type": "slide_chunk", "index": index, "content": html_part}
                            trailing_text += chunk_content[end_pos:]
                        else:
                            full_html += chunk_content
                            yield {"type": "slide_chunk", "index": index, "content": chunk_content}
                    else:
                        full_html += chunk_content
                        yield {"type": "slide_chunk", "index": index, "content": chunk_content}
                else:
                    trailing_text += chunk_content

        if full_html.rstrip().endswith("```"):
            full_html = full_html.rstrip()
            full_html = full_html[:-3].rstrip()

        full_html = repair_html(full_html)

        if not html_started or "</html>" not in full_html.lower():
            failed_slides.append(index + 1)
            yield {"type": "text", "content": f"\n⚠️ 第 {index + 1} 页生成失败，跳过继续生成后续页\n"}
            continue

        prev_html = full_html

        yield {"type": "slide_end", "index": index}

    # 总结
    ending = trailing_text.strip().rstrip("`").strip()
    if ending:
        yield {"type": "text", "content": ending}
    else:
        slide_titles = [s.get("title", "") for s in slides]
        total = len(slides)
        generated = total - len(failed_slides)

        summary_prompt = (
            f"你刚刚为用户生成了一份关于「{user_msg}」的 PPT，共 {total} 页。\n"
            f"各页标题：{'、'.join(slide_titles)}\n"
        )
        if failed_slides:
            summary_prompt += f"其中第 {', '.join(map(str, failed_slides))} 页生成失败。\n"
        summary_prompt += (
            "\n请用 2-3 句话总结这份 PPT 的内容结构和亮点，语气自然友好，"
            "并简要提示用户可以如何使用或修改这份演示文稿。不要重复列出每页标题。"
        )

        summary_messages = [
            {"role": "system", "content": "你是一个 PPT 助手，擅长用简洁友好的语言总结演示文稿。"},
            {"role": "user", "content": summary_prompt},
        ]

        stream = await client.chat.completions.create(
            model="mimo-v2.5-pro",
            messages=summary_messages,
            stream=True,
            extra_body={"thinking": {"type": "disabled"}},
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield {"type": "text", "content": delta.content}

    yield {"type": "done", "content": True}
```

- [ ] **Step 2: 验证语法正确**

Run: `cd /Users/xlw/Documents/GitHub/EasyAgent-backend && python -c "from utils.openai_client import ppt_slide_stream; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add utils/openai_client.py
git commit -m "feat: add ppt_slide_stream() for slide-only generation"
```

---

### Task 4: 新增 `POST /chat/ppt_outline` 端点

**Files:**
- Modify: `router/chat.py`（在 `upload_chat_file` 端点之后、`create_chat_router` 之前添加）

- [ ] **Step 1: 添加 `ppt_outline` 端点**

在 `router/chat.py` 的 `upload_chat_file` 函数（约第 106 行）之后添加：

```python
# PPT 大纲生成（SSE 流）
@router.post("/ppt_outline")
async def ppt_outline_endpoint(
    chatData: dict,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    from utils.openai_client import ppt_outline_stream

    doc_ids = chatData.get("doc_ids")
    file_ids = chatData.get("file_ids")

    # 处理附件（复用 /stream 的逻辑）
    file_attachments = []
    if file_ids:
        attachments = get_attachments_by_ids(db, file_ids)
        for att in attachments:
            if is_image_file(att.filename):
                try:
                    response = minio_client.get_object(minio_bucket, att.minio_key)
                    file_bytes = response.read()
                    response.close()
                    response.release_conn()
                    b64_url = image_to_base64(att.filename, file_bytes)
                    file_attachments.append({"filename": att.filename, "text_content": None, "image_base64": b64_url})
                except Exception:
                    file_attachments.append({"filename": att.filename, "text_content": "(图片读取失败)", "image_base64": None})
            else:
                file_attachments.append({"filename": att.filename, "text_content": att.text_content or "(无内容)", "image_base64": None})

    # RAG 引用
    user_rag_refs = None
    if doc_ids:
        from models.knowledge import KnowledgeDocument
        docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.id.in_(doc_ids)).all()
        user_rag_refs = [{"doc_id": d.id, "filename": d.filename, "file_type": d.file_type} for d in docs]

    # 创建用户消息
    user_message = create_message(db, chatData.get("id"), chatData.get("message"), 0, None, message_type="text", rag_references=user_rag_refs)

    if doc_ids and user_message:
        from crud.knowledge import bind_docs_to_message
        bind_docs_to_message(db, doc_ids, chatData.get("id"), user_message.id)

    if file_ids and user_message:
        bind_attachments_to_message(db, file_ids, chatData.get("id"), user_message.id)

    # 构建 LLM 消息
    message_obj = get_chat_messages(db, chatData.get("id"))
    message_out = [Message.model_validate(m) for m in message_obj]
    messages_for_llm = [
        {"role": "user" if msg.sender == 0 else "assistant", "content": msg.content}
        for msg in message_out
    ]

    # 拼入附件内容
    if file_attachments and messages_for_llm:
        has_images = any(f.get("image_base64") for f in file_attachments)
        text_parts = []
        for f in file_attachments:
            if f.get("text_content"):
                text_parts.append(f"[附件: {f['filename']}]\n{f['text_content']}")

        if has_images:
            content_array = []
            original_text = messages_for_llm[-1]["content"] or ""
            if text_parts:
                original_text += "\n\n---\n" + "\n\n".join(text_parts)
            content_array.append({"type": "text", "text": original_text})
            for f in file_attachments:
                if f.get("image_base64"):
                    content_array.append({"type": "image_url", "image_url": {"url": f["image_base64"]}})
            messages_for_llm[-1]["content"] = content_array
        elif text_parts:
            original_text = messages_for_llm[-1]["content"] or ""
            messages_for_llm[-1]["content"] = original_text + "\n\n---\n" + "\n\n".join(text_parts)

    # 创建 AI 消息占位
    ai_msg = create_message(db, chatData.get("id"), "", 1, None, message_type="ppt")
    if not ai_msg:
        return ResponseSchema.fail(message="创建AI消息失败", data=None)
    ai_msg_out = Message.model_validate(ai_msg)

    # 大纲数据收集
    outline_slides = []
    outline_style = {}
    think_parts = []
    tool_calls_data = []
    tool_call_map = {}
    outline_tool_call_id = None

    cancel_event = asyncio.Event()

    async def outline_event_generator():
        nonlocal outline_slides, outline_style, think_parts, tool_calls_data, tool_call_map, outline_tool_call_id
        try:
            async for chunk in ppt_outline_stream(messages_for_llm, cancel_event=cancel_event):
                if not chunk:
                    continue
                chunk_type = chunk.get("type")

                if chunk_type == "think":
                    think_parts.append(chunk["content"])
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif chunk_type == "tool_start":
                    tool_name = chunk['tool']
                    tool_run_id = chunk.get("tool_run_id", tool_name)
                    tool_obj = add_tool_call(db=db, message_id=ai_msg_out.id, tool_name=tool_name, tool_input=chunk['args'])
                    tool_obj_out = ToolCall.model_validate(tool_obj)
                    tool_calls_data.append(tool_obj_out)
                    tool_call_map[tool_run_id] = tool_obj_out
                    yield f"data: {json.dumps({'type': 'tool_name', 'tool_name': tool_obj_out.model_dump(mode='json')}, ensure_ascii=False)}\n\n"

                elif chunk_type == "tool_mid":
                    tool_run_id = chunk.get("tool_run_id", chunk.get("tool"))
                    tool_content_str = chunk.get("tool_content")
                    try:
                        current_tool_content = json.dumps(tool_content_str, ensure_ascii=False)
                    except (TypeError, json.JSONDecodeError):
                        current_tool_content = str(tool_content_str)
                    matching_tool = tool_call_map.get(tool_run_id)
                    if not matching_tool:
                        continue
                    res_obj = update_tool_message(db=db, tool_call_id=matching_tool.id, tool_content=current_tool_content)
                    res_obj_out = ToolCall.model_validate(res_obj).model_dump(mode="json")
                    res_obj_out["message_id"] = chatData.get("id")
                    yield f"data: {json.dumps({'type': 'tool_content', 'tool_content': res_obj_out}, ensure_ascii=False)}\n\n"

                elif chunk_type == "outline":
                    outline_slides = chunk.get("slides", [])
                    outline_style = chunk.get("style", {})
                    # 存入 DB
                    outline_data = json.dumps({"slides": outline_slides, "style": outline_style}, ensure_ascii=False)
                    tool_obj = add_tool_call(
                        db=db, message_id=ai_msg_out.id,
                        tool_name="ppt_outline", tool_content=outline_data,
                        tool_input=chatData.get("message"),
                    )
                    outline_tool_call_id = tool_obj.id
                    # 更新消息内容（存储大纲摘要）
                    update_message_content(db, ai_msg.id, f"已生成 {len(outline_slides)} 页大纲", "\n".join(think_parts) if think_parts else None)
                    # 返回大纲 + message_id
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif chunk_type == "error":
                    update_message_content(db, ai_msg.id, "", "\n".join(think_parts) if think_parts else None)
                    yield f"event: error\ndata: {json.dumps({'error': chunk['content']}, ensure_ascii=False)}\n\n"
                    return

            # 流结束，返回 message_id 供前端后续调用
            if not cancel_event.is_set():
                yield f"event: done\ndata: {json.dumps({'done': True, 'message_id': ai_msg_out.id})}\n\n"

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            cancel_event.set()
            update_message_content(db, ai_msg.id, "", "\n".join(think_parts) if think_parts else None)
        except Exception as e:
            update_message_content(db, ai_msg.id, "", "\n".join(think_parts) if think_parts else None)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(outline_event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: 验证服务启动无报错**

Run: `cd /Users/xlw/Documents/GitHub/EasyAgent-backend && python -c "from router.chat import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add router/chat.py
git commit -m "feat: add POST /chat/ppt_outline endpoint"
```

---

### Task 5: 新增 `POST /chat/update_outline` 端点

**Files:**
- Modify: `router/chat.py`（在 `ppt_outline_endpoint` 之后添加）

- [ ] **Step 1: 添加请求 schema 和端点**

在 `router/chat.py` 的 imports 区域添加需要的 schema（如果还没有），然后在 `ppt_outline_endpoint` 之后添加：

```python
# 更新 PPT 大纲
@router.post("/update_outline", response_model=ResponseSchema)
async def update_outline_endpoint(
    data: dict,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    from crud.messages import get_tool_call_by_message_and_name

    message_id = data.get("message_id")
    outline = data.get("outline")

    if not message_id or not outline:
        return ResponseSchema.fail(message="缺少 message_id 或 outline 参数")

    slides = outline.get("slides")
    style = outline.get("style")
    if not slides or not isinstance(slides, list) or len(slides) == 0:
        return ResponseSchema.fail(message="至少需要保留一页幻灯片")
    if not style or not isinstance(style, dict):
        return ResponseSchema.fail(message="缺少 style 对象")

    # 查找大纲记录
    tool_call = get_tool_call_by_message_and_name(db, message_id, "ppt_outline")
    if not tool_call:
        return ResponseSchema.fail(message="大纲记录不存在")
    if tool_call.status != 2:
        return ResponseSchema.fail(message="大纲已确认或已取消，无法修改")

    # 更新内容
    outline_data = json.dumps({"slides": slides, "style": style}, ensure_ascii=False)
    update_tool_content(db, tool_call.id, outline_data)

    return ResponseSchema.ok(message="大纲更新成功")
```

- [ ] **Step 2: 验证导入无误**

Run: `cd /Users/xlw/Documents/GitHub/EasyAgent-backend && python -c "from router.chat import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add router/chat.py
git commit -m "feat: add POST /chat/update_outline endpoint"
```

---

### Task 6: 新增 `POST /chat/ppt_generate` 端点

**Files:**
- Modify: `router/chat.py`（在 `update_outline_endpoint` 之后添加）

- [ ] **Step 1: 添加 `ppt_generate` 端点**

```python
# PPT 生成（SSE 流）— 从已确认的大纲生成幻灯片
@router.post("/ppt_generate")
async def ppt_generate_endpoint(
    chatData: dict,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    from utils.openai_client import ppt_slide_stream
    from crud.messages import get_tool_call_by_message_and_name

    message_id = chatData.get("message_id")
    if not message_id:
        return ResponseSchema.fail(message="缺少 message_id 参数")

    # 查找大纲记录
    outline_tool = get_tool_call_by_message_and_name(db, message_id, "ppt_outline")
    if not outline_tool:
        return ResponseSchema.fail(message="大纲记录不存在")
    if outline_tool.status != 2:
        return ResponseSchema.fail(message="大纲已确认或已取消")

    # 解析大纲
    try:
        outline_data = json.loads(outline_tool.tool_content)
        slides = outline_data.get("slides", [])
        style = outline_data.get("style", {})
    except (json.JSONDecodeError, AttributeError):
        return ResponseSchema.fail(message="大纲数据格式错误")

    if not slides:
        return ResponseSchema.fail(message="大纲为空，无法生成 PPT")

    # 标记大纲为已确认
    outline_tool.status = 1
    db.commit()

    # 获取用户原始消息（用于 PPT 生成上下文）
    user_msg = outline_tool.tool_input or ""

    # 创建 PPT 工具调用记录（初始 status=2，完成后更新为 1）
    ai_msg = create_message(db, chatData.get("id"), "", 1, None, message_type="ppt")
    if not ai_msg:
        return ResponseSchema.fail(message="创建AI消息失败", data=None)
    ai_msg_out = Message.model_validate(ai_msg)

    slides_html = {}
    text_parts = []
    think_parts = []
    ppt_tool_call_id = None

    def save_ppt_incremental():
        nonlocal ppt_tool_call_id
        if not slides_html:
            return
        ppt_data = {
            "slides": [
                {"index": i, "html": slides_html.get(i, "")}
                for i in sorted(slides_html.keys())
            ]
        }
        ppt_content = json.dumps(ppt_data, ensure_ascii=False)
        if ppt_tool_call_id is None:
            tool_obj = add_tool_call(
                db=db, message_id=ai_msg_out.id,
                tool_name="ppt", tool_content=ppt_content,
                tool_input=user_msg,
            )
            ppt_tool_call_id = tool_obj.id
        else:
            update_tool_content(db=db, tool_call_id=ppt_tool_call_id, tool_content=ppt_content)

    cancel_event = asyncio.Event()

    async def ppt_event_generator():
        nonlocal slides_html, text_parts, think_parts, ppt_tool_call_id
        try:
            async for chunk in ppt_slide_stream(slides, style, user_msg, cancel_event=cancel_event):
                if not chunk:
                    continue
                chunk_type = chunk.get("type")

                if chunk_type == "think":
                    think_parts.append(chunk["content"])
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif chunk_type == "text":
                    text_parts.append(chunk["content"])
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif chunk_type == "slide_start":
                    slides_html[chunk["index"]] = ""
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif chunk_type == "slide_chunk":
                    idx = chunk["index"]
                    slides_html[idx] += chunk["content"]
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif chunk_type == "slide_end":
                    save_ppt_incremental()
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif chunk_type == "error":
                    text_content = "\n".join(text_parts) if text_parts else ""
                    think_content = "\n".join(think_parts) if think_parts else None
                    update_message_content(db, ai_msg.id, text_content, think_content)
                    save_ppt_incremental()
                    yield f"event: error\ndata: {json.dumps({'error': chunk['content']}, ensure_ascii=False)}\n\n"
                    return

                elif chunk_type == "done":
                    text_content = "\n".join(text_parts) if text_parts else ""
                    think_content = "\n".join(think_parts) if think_parts else None
                    update_message_content(db, ai_msg.id, text_content, think_content)

                    ppt_data = {
                        "slides": [
                            {"index": i, "html": slides_html.get(i, "")}
                            for i in sorted(slides_html.keys())
                        ]
                    }
                    if ppt_tool_call_id is None:
                        add_tool_call(
                            db=db, message_id=ai_msg_out.id,
                            tool_name="ppt",
                            tool_content=json.dumps(ppt_data, ensure_ascii=False),
                            tool_input=user_msg,
                        )
                    else:
                        update_tool_message(
                            db=db, tool_call_id=ppt_tool_call_id,
                            tool_content=json.dumps(ppt_data, ensure_ascii=False),
                        )

                    yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            cancel_event.set()
            text_content = "\n".join(text_parts) if text_parts else ""
            think_content = "\n".join(think_parts) if think_parts else None
            update_message_content(db, ai_msg.id, text_content, think_content)
            save_ppt_incremental()
        except Exception as e:
            text_content = "\n".join(text_parts) if text_parts else ""
            think_content = "\n".join(think_parts) if think_parts else None
            update_message_content(db, ai_msg.id, text_content, think_content)
            save_ppt_incremental()
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(ppt_event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: 验证服务启动无报错**

Run: `cd /Users/xlw/Documents/GitHub/EasyAgent-backend && python -c "from router.chat import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add router/chat.py
git commit -m "feat: add POST /chat/ppt_generate endpoint"
```

---

### Task 7: 更新前端集成指南中的 `message_id` 获取方式

**Files:**
- Modify: `docs/superpowers/specs/2026-05-27-ppt-outline-frontend-guide.md`

- [ ] **Step 1: 确认 `done` 事件已包含 `message_id`**

在 Task 4 的 `outline_event_generator` 中，`done` 事件已包含 `message_id`：
```python
yield f"event: done\ndata: {json.dumps({'done': True, 'message_id': ai_msg_out.id})}\n\n"
```

前端集成指南中已标注此需求，无需额外修改。

- [ ] **Step 2: Commit（如果做了修改）**

```bash
git add docs/
git commit -m "docs: finalize frontend integration guide"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 启动服务确认无报错**

Run: `cd /Users/xlw/Documents/GitHub/EasyAgent-backend && python -c "from main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 2: 检查所有新端点已注册**

Run: `cd /Users/xlw/Documents/GitHub/EasyAgent-backend && python -c "from main import app; routes = [r.path for r in app.routes]; print('/chat/ppt_outline' in routes); print('/chat/update_outline' in routes); print('/chat/ppt_generate' in routes)"`
Expected: `True` `True` `True`

- [ ] **Step 3: Final commit（如有遗漏）**

```bash
git status
# 检查是否有未提交的更改
```
