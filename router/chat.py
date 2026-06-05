from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from utils.utils import get_current_user
from schemas.chat import CreateChat, ChatItem, AllChatItem
from schemas.messages import Message, ToolCall
from crud.chat import create_chat, get_chat_by_user_id, update_chat_title, delete_chat
from crud.messages import create_message, get_chat_messages, add_tool_call, update_tool_message, update_tool_content, get_tool_call_by_id, update_message_content
from crud.chat_share import cancel_chat_share_api
from crud.chat_attachment import create_attachment, get_attachments_by_ids, bind_attachments_to_message
from schemas.response import ResponseSchema
from database import get_db
from sqlalchemy.orm import Session
import json
import time
import uuid
import io
import asyncio
from utils.openai_client import chat_stream, generate_chat_title, ppt_stream, ppt_outline_stream
from utils.rag_service import get_rag_service
from utils.document_parser import validate_file, parse_document, is_text_file, is_image_file, image_to_base64
from minio import Minio
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

# MinIO client (same config as router/user.py)
minio_client = Minio(
    endpoint='127.0.0.1:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)
minio_bucket = "easy-agent"


# 上传聊天附件
@router.post("/upload_file", response_model=ResponseSchema)
async def upload_chat_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)

        # 校验文件类型和大小
        error = validate_file(file.filename, file_size)
        if error:
            return ResponseSchema.fail(message=error)

        # 生成唯一 object key
        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        minio_key = f"chat_attachments/{unique_name}"

        # 上传到 MinIO
        minio_client.put_object(
            bucket_name=minio_bucket,
            object_name=minio_key,
            data=io.BytesIO(file_bytes),
            length=file_size,
            content_type=file.content_type,
        )

        # 生成 presigned URL
        file_url = minio_client.presigned_get_object(
            bucket_name=minio_bucket,
            object_name=minio_key,
        )

        # 解析文本文件内容
        text_content = None
        if is_text_file(file.filename):
            try:
                text_content = parse_document(file.filename, file_bytes)
            except Exception:
                text_content = None

        # 写入数据库
        attachment = create_attachment(
            db=db,
            chat_id=None,
            filename=file.filename,
            file_type=ext.lower(),
            file_size=file_size,
            minio_key=minio_key,
            file_url=file_url,
            text_content=text_content,
        )

        return ResponseSchema.ok(
            message="上传成功",
            data={
                "file_id": attachment.id,
                "filename": attachment.filename,
                "file_type": attachment.file_type,
                "file_size": attachment.file_size,
                "file_url": attachment.file_url,
                "text_content": attachment.text_content,
            },
        )
    except Exception as e:
        return ResponseSchema.fail(message=f"上传失败: {str(e)}")


# PPT 大纲生成（SSE 流）— 支持新生成和重新生成
@router.post("/ppt_outline")
async def ppt_outline_endpoint(
    chatData: dict,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    from crud.messages import get_tool_call_by_message_and_name, get_message_by_id, delete_tool_calls_by_message, reset_outline_for_regenerate

    message_id = chatData.get("message_id")  # 重新生成时传入
    is_regenerate = message_id is not None

    if is_regenerate:
        # === 重新生成模式 ===
        outline_tool = get_tool_call_by_message_and_name(db, message_id, "ppt_outline")
        if not outline_tool:
            return ResponseSchema.fail(message="大纲记录不存在")

        user_msg = outline_tool.tool_input or ""
        if not user_msg:
            return ResponseSchema.fail(message="无法获取原始用户消息")

        outline_message = get_message_by_id(db, message_id)
        if not outline_message:
            return ResponseSchema.fail(message="大纲消息不存在")

        chat_id = outline_message.chat_id

        # 获取聊天历史上下文（当前消息之前的所有消息）
        all_messages = get_chat_messages(db, chat_id)
        messages_for_llm = []
        for msg in all_messages:
            if msg.id == message_id:
                break
            content = msg.content or ""
            if content:
                messages_for_llm.append({
                    "role": "user" if msg.sender == 0 else "assistant",
                    "content": content
                })

        # 获取附件信息
        file_attachments = []
        if outline_message.attachments:
            for att in outline_message.attachments:
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

        # 拼入附件内容到最后一条用户消息
        if file_attachments and messages_for_llm:
            has_images = any(f.get("image_base64") for f in file_attachments)
            text_parts = []
            for f in file_attachments:
                if f.get("text_content"):
                    text_parts.append(f"[附件: {f['filename']}]\n{f['text_content']}")

            for msg in reversed(messages_for_llm):
                if msg["role"] == "user":
                    if has_images:
                        content_array = []
                        original_text = msg["content"] or ""
                        if text_parts:
                            original_text += "\n\n---\n" + "\n\n".join(text_parts)
                        content_array.append({"type": "text", "text": original_text})
                        for f in file_attachments:
                            if f.get("image_base64"):
                                content_array.append({"type": "image_url", "image_url": {"url": f["image_base64"]}})
                        msg["content"] = content_array
                    elif text_parts:
                        original_text = msg["content"] or ""
                        msg["content"] = original_text + "\n\n---\n" + "\n\n".join(text_parts)
                    break

        if not messages_for_llm:
            messages_for_llm = [{"role": "user", "content": user_msg}]

        # 清理原有的工具调用记录（保留 ppt_outline 本身）并重置大纲状态
        delete_tool_calls_by_message(db, message_id, exclude_tool_name="ppt_outline")
        reset_outline_for_regenerate(db, outline_tool.id)

        # 使用原有 AI 消息
        ai_msg_out = Message.model_validate(outline_message)

    else:
        # === 新生成模式 ===
        doc_ids = chatData.get("doc_ids")
        file_ids = chatData.get("file_ids")

        # 处理附件
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

    cancel_event = asyncio.Event()

    async def outline_event_generator():
        nonlocal outline_slides, outline_style, think_parts, tool_calls_data, tool_call_map
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
                    outline_data = json.dumps({"slides": outline_slides, "style": outline_style}, ensure_ascii=False)

                    if is_regenerate:
                        # 更新原有大纲记录
                        update_tool_content(db, outline_tool.id, outline_data)
                    else:
                        # 创建新大纲记录
                        tool_obj = add_tool_call(
                            db=db, message_id=ai_msg_out.id,
                            tool_name="ppt_outline", tool_content=outline_data,
                            tool_input=chatData.get("message"),
                        )

                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif chunk_type == "error":
                    if not is_regenerate:
                        update_message_content(db, ai_msg_out.id, "", "\n".join(think_parts) if think_parts else None)
                    yield f"event: error\ndata: {json.dumps({'error': chunk['content']}, ensure_ascii=False)}\n\n"
                    return

            # 流结束
            if not cancel_event.is_set():
                yield f"event: done\ndata: {json.dumps({'done': True, 'message_id': ai_msg_out.id})}\n\n"

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            cancel_event.set()
            if not is_regenerate:
                update_message_content(db, ai_msg_out.id, "", "\n".join(think_parts) if think_parts else None)
        except Exception as e:
            if not is_regenerate:
                update_message_content(db, ai_msg_out.id, "", "\n".join(think_parts) if think_parts else None)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(outline_event_generator(), media_type="text/event-stream")


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
        return ResponseSchema.fail(message=f"大纲记录不存在 (message_id={message_id})")
    if tool_call.status != 2:
        return ResponseSchema.fail(message=f"大纲状态为 {tool_call.status}，无法修改（仅状态=2可修改）")

    # 更新内容
    outline_data = json.dumps({"slides": slides, "style": style}, ensure_ascii=False)
    update_tool_content(db, tool_call.id, outline_data)

    return ResponseSchema.ok(message="大纲更新成功")


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

    # 获取用户原始消息
    user_msg = outline_tool.tool_input or ""

    # 创建 PPT 工具调用记录
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
                    update_message_content(db, message_id, text_content, think_content)
                    save_ppt_incremental()
                    yield f"event: error\ndata: {json.dumps({'error': chunk['content']}, ensure_ascii=False)}\n\n"
                    return

                elif chunk_type == "done":
                    text_content = "\n".join(text_parts) if text_parts else ""
                    think_content = "\n".join(think_parts) if think_parts else None
                    update_message_content(db, message_id, text_content, think_content)

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
            update_message_content(db, message_id, text_content, think_content)
            save_ppt_incremental()
        except Exception as e:
            text_content = "\n".join(text_parts) if text_parts else ""
            think_content = "\n".join(think_parts) if think_parts else None
            update_message_content(db, message_id, text_content, think_content)
            save_ppt_incremental()
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(ppt_event_generator(), media_type="text/event-stream")


# 创建新聊天
@router.post('/create_chat', response_model=ResponseSchema)
async def create_chat_router(chatData: CreateChat, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    title = await generate_chat_title(chatData.message)
    # 创建聊天对象
    chat_obj = create_chat(db, user, chatData.id,title)
    if not chat_obj:
        return ResponseSchema.fail(message="创建聊天失败", data=None)
    chat_out = ChatItem.model_validate(chat_obj)
    return ResponseSchema.ok(message="创建聊天成功", data=chat_out)


# 创建聊天
@router.post("/stream")
async def create_chat_router(
    chatData: dict,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    mode = chatData.get("mode", "text")
    doc_ids = chatData.get("doc_ids")  # @ 选中的文档 ID 列表
    file_ids = chatData.get("file_ids")  # 聊天附件 ID 列表

    # 处理附件：文本文件直接用数据库中已解析的内容，图片需要从 MinIO 下载转 base64
    file_attachments = []  # [{filename, text_content, image_base64}]
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

    # 构建用户消息的引用信息（记录用户 @ 了哪些文档）
    user_rag_refs = None
    if doc_ids:
        from models.knowledge import KnowledgeDocument
        docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.id.in_(doc_ids)).all()
        user_rag_refs = [
            {"doc_id": d.id, "filename": d.filename, "file_type": d.file_type}
            for d in docs
        ]

    # 用户消息始终 message_type="text"
    user_message = create_message(db, chatData.get("id"), chatData.get("message"), 0, None, message_type="text", rag_references=user_rag_refs)

    # 绑定文档到消息
    if doc_ids and user_message:
        from crud.knowledge import bind_docs_to_message
        bind_docs_to_message(db, doc_ids, chatData.get("id"), user_message.id)

    # 绑定附件到消息
    if file_ids and user_message:
        bind_attachments_to_message(db, file_ids, chatData.get("id"), user_message.id)

    message_obj = get_chat_messages(db, chatData.get("id"))
    message_out = [Message.model_validate(m) for m in message_obj]
    messages_for_llm = [
        {"role": "user" if msg.sender == 0 else "assistant", "content": msg.content}
        for msg in message_out
    ]

    # 将附件内容拼入最后一条用户消息
    if file_attachments and messages_for_llm:
        has_images = any(f.get("image_base64") for f in file_attachments)
        # 构建附件文本部分
        text_parts = []
        for f in file_attachments:
            if f.get("text_content"):
                text_parts.append(f"[附件: {f['filename']}]\n{f['text_content']}")

        if has_images:
            # 多模态格式：content 为数组
            content_array = []
            original_text = messages_for_llm[-1]["content"] or ""
            if text_parts:
                original_text += "\n\n---\n" + "\n\n".join(text_parts)
            content_array.append({"type": "text", "text": original_text})
            for f in file_attachments:
                if f.get("image_base64"):
                    content_array.append({
                        "type": "image_url",
                        "image_url": {"url": f["image_base64"]}
                    })
            messages_for_llm[-1]["content"] = content_array
        elif text_parts:
            # 纯文本附件，直接拼接
            original_text = messages_for_llm[-1]["content"] or ""
            messages_for_llm[-1]["content"] = original_text + "\n\n---\n" + "\n\n".join(text_parts)

    # RAG: retrieve context
    rag_context = None
    rag_references = []

    if doc_ids:
        # @ 选中特定文档，按 doc_ids 过滤检索
        from models.knowledge import KnowledgeDocument, KnowledgeBase
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_ids[0]).first()
        if doc:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc.kb_id).first()
            if kb:
                rag = get_rag_service()
                user_query = chatData.get("message", "")
                chunks = rag.retrieve(kb.chroma_collection, user_query, doc_ids=doc_ids)
                if chunks:
                    rag_context = rag.build_context(chunks)
                    rag_references = rag.build_references(chunks)
    else:
        # 自动检索：全局知识库 + 当前会话专属文档
        from models.knowledge import KnowledgeBase, KnowledgeDocument
        from crud.knowledge import get_or_create_global_kb, get_chat_doc_list
        kb = get_or_create_global_kb(db, user)
        rag = get_rag_service()
        user_query = chatData.get("message", "")

        # 收集要检索的 doc_ids：全局文档 + 当前会话文档
        global_docs = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.kb_id == kb.id,
            KnowledgeDocument.chat_id.is_(None),
            KnowledgeDocument.message_id.is_(None),
            KnowledgeDocument.status == "completed"
        ).all()
        chat_docs = get_chat_doc_list(db, chatData.get("id"))
        chat_docs = [d for d in chat_docs if d.status == "completed"]

        all_doc_ids = [d.id for d in global_docs] + [d.id for d in chat_docs]

        if all_doc_ids:
            chunks = rag.retrieve(kb.chroma_collection, user_query, doc_ids=all_doc_ids)
            if chunks:
                rag_context = rag.build_context(chunks)
                rag_references = rag.build_references(chunks)

    if mode == "ppt":
        # PPT 模式
        ai_msg = create_message(db, chatData.get("id"), "", 1, None, message_type="ppt")
        if not ai_msg:
            return ResponseSchema.fail(message="创建AI消息失败", data=None)
        ai_msg_out = Message.model_validate(ai_msg)

        # 收集大纲、各页 HTML 和文本内容，用于增量落库
        outline_data = []
        style_data = {}
        slides_html = {}  # index -> full_html
        text_parts = []   # 收集文本部分
        think_parts = []  # 收集思考内容
        tool_calls_data = []  # 存储工具调用
        tool_call_map = {}    # tool_run_id -> ToolCall db对象
        ppt_tool_call_id = None  # PPT 主记录 ID，大纲生成后创建

        def save_ppt_incremental():
            """将当前已收集的 PPT 数据增量写入数据库"""
            nonlocal ppt_tool_call_id
            if not outline_data and not slides_html:
                return
            ppt_data = {
                "outline": outline_data,
                "style": style_data,
                "slides": [
                    {"index": i, "html": slides_html.get(i, "")}
                    for i in sorted(slides_html.keys())
                ]
            }
            ppt_content = json.dumps(ppt_data, ensure_ascii=False)
            if ppt_tool_call_id is None:
                # 首次创建 PPT 主记录
                tool_obj = add_tool_call(
                    db=db, message_id=ai_msg_out.id,
                    tool_name="ppt", tool_content=ppt_content,
                    tool_input=chatData.get("message"),
                )
                ppt_tool_call_id = tool_obj.id
            else:
                # 增量更新，保持 status=2（进行中）
                update_tool_content(db=db, tool_call_id=ppt_tool_call_id, tool_content=ppt_content)

        cancel_event = asyncio.Event()

        async def ppt_event_generator():
            nonlocal outline_data, style_data, slides_html, text_parts, think_parts, tool_calls_data, tool_call_map, ppt_tool_call_id
            try:
                async for chunk in ppt_stream(messages_for_llm, cancel_event=cancel_event):
                    if not chunk:
                        continue
                    chunk_type = chunk.get("type")

                    if chunk_type == "think":
                        think_parts.append(chunk["content"])
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                    elif chunk_type == "text":
                        text_parts.append(chunk["content"])
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
                        outline_data = chunk.get("slides", [])
                        style_data = chunk.get("style", {})
                        save_ppt_incremental()
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
                        # 保存已有的部分数据，不删除消息
                        text_content = "\n".join(text_parts) if text_parts else ""
                        think_content = "\n".join(think_parts) if think_parts else None
                        update_message_content(db, ai_msg.id, text_content, think_content)
                        save_ppt_incremental()
                        yield f"event: error\ndata: {json.dumps({'error': chunk['content']}, ensure_ascii=False)}\n\n"
                        return

                    elif chunk_type == "done":
                        # text 内容存入 Message.content
                        text_content = "\n".join(text_parts) if text_parts else ""
                        think_content = "\n".join(think_parts) if think_parts else None
                        update_message_content(db, ai_msg.id, text_content, think_content)

                        # 最终完整 PPT 数据写入，标记为完成（status=1）
                        ppt_data = {
                            "outline": outline_data,
                            "style": style_data,
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
                                tool_input=chatData.get("message"),
                            )
                        else:
                            update_tool_message(
                                db=db, tool_call_id=ppt_tool_call_id,
                                tool_content=json.dumps(ppt_data, ensure_ascii=False),
                            )

                        yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"

            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                # 客户端断开连接，停止 LLM 推理并保存已有的部分数据
                cancel_event.set()
                text_content = "\n".join(text_parts) if text_parts else ""
                think_content = "\n".join(think_parts) if think_parts else None
                update_message_content(db, ai_msg.id, text_content, think_content)
                save_ppt_incremental()
            except Exception as e:
                # 保留已有的部分数据，不删除消息
                text_content = "\n".join(text_parts) if text_parts else ""
                think_content = "\n".join(think_parts) if think_parts else None
                update_message_content(db, ai_msg.id, text_content, think_content)
                save_ppt_incremental()
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(ppt_event_generator(), media_type="text/event-stream")

    else:
        # 普通文本模式（现有逻辑）
        # 预创建 AI 消息占位，tool_call 将关联到此消息
        ai_msg = create_message(db, chatData.get("id"), "", 1, None)
        if not ai_msg:
            return ResponseSchema.fail(message="创建AI消息失败", data=None)
        ai_msg_out = Message.model_validate(ai_msg)
        formal_content = ""
        think_content = ""
        tool_calls_data = []  # 存储多个工具调用
        tool_call_map = {}  # tool_run_id -> ToolCall db对象，用于匹配并行工具调用

        cancel_event = asyncio.Event()

        async def event_generator():
            nonlocal formal_content, think_content, tool_calls_data, tool_call_map, rag_references
            try:
                async for chunk in chat_stream(messages_for_llm, context=rag_context, cancel_event=cancel_event):
                    if not chunk:
                        continue

                    chunk_type = chunk.get("type")
                    content = chunk.get("content")

                    if chunk_type == "tool_start":
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

                    elif chunk_type == "think":
                        think_content += content
                        yield f"data: {json.dumps({'content': content, 'type': 'think'}, ensure_ascii=False)}\n\n"

                    elif chunk_type == "text" and content is not None:
                        formal_content += content
                        yield f"data: {json.dumps({'content': content, 'type': 'text'}, ensure_ascii=False)}\n\n"
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                # 客户端断开连接，停止 LLM 推理并保存已有的部分数据
                cancel_event.set()
                update_message_content(db, ai_msg.id, formal_content, think_content, rag_references)
            except Exception as e:
                # RAG context 导致 LLM 报错时，回退到普通对话重试
                if rag_context:
                    formal_content = ""
                    think_content = ""
                    rag_references = []
                    try:
                        async for chunk in chat_stream(messages_for_llm, context=None, cancel_event=cancel_event):
                            if not chunk:
                                continue
                            chunk_type = chunk.get("type")
                            content = chunk.get("content")
                            if chunk_type == "think":
                                think_content += content
                                yield f"data: {json.dumps({'content': content, 'type': 'think'}, ensure_ascii=False)}\n\n"
                            elif chunk_type == "text" and content is not None:
                                formal_content += content
                                yield f"data: {json.dumps({'content': content, 'type': 'text'}, ensure_ascii=False)}\n\n"
                    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                        cancel_event.set()
                        update_message_content(db, ai_msg.id, formal_content, think_content, [])
                    except Exception as e2:
                        yield f"event: error\ndata: {json.dumps({'error': str(e2)})}\n\n"
                else:
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

            # 更新 AI 消息内容（仅在非客户端断开异常时执行）
            if not cancel_event.is_set():
                update_message_content(db, ai_msg.id, formal_content, think_content, rag_references)

                # Send references if available
                if rag_references:
                    yield f"data: {json.dumps({'references': rag_references}, ensure_ascii=False)}\n\n"

                yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

# 查询对应用户的所有聊天
@router.get('/get_chat_list',response_model=ResponseSchema)
async def get_chat_list_router(db:Session = Depends(get_db), user: str = Depends(get_current_user),page_size:int=200,last_id:int|None=None):
    user_id = user
    chat_list =get_chat_by_user_id(db,user_id,page_size,last_id)
    if not chat_list:
        return ResponseSchema.fail(message="查询聊天列表失败",data=None)
    chat_list_out = [AllChatItem.model_validate(chat) for chat in chat_list["data"]]

    return ResponseSchema.ok(message="查询聊天列表成功",data={"chat_list":chat_list_out,"next_last_id":chat_list["next_last_id"]})

@router.get('/get_chat_message/{chat_id}',response_model=ResponseSchema)
async def get_chat_message_router(chat_id:int,db:Session = Depends(get_db), _: str = Depends(get_current_user)):
    chat_obj = get_chat_messages(db,chat_id)
    if not chat_obj:
        return ResponseSchema.fail(message="查询聊天消息失败",data=None)
    chat_out = [Message.model_validate(message, from_attributes=True) for message in chat_obj]
    return ResponseSchema.ok(message="查询聊天消息成功",data=chat_out)

# 更新聊天标题
@router.post('/update_chat_title',response_model=ResponseSchema)
async def update_chat_title_router(chatData: CreateChat, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    chat = update_chat_title(db,user,chatData.id,chatData.message)
    if not chat:
        return ResponseSchema.fail(message="更新聊天标题失败",data=None)
    chat_obj = ChatItem.model_validate(chat)
    return ResponseSchema.ok(message="更新聊天标题成功",data=chat_obj)

# 删除聊天
@router.delete('/delete_chat/{chat_id}',response_model=ResponseSchema)
async def delete_chat_router(chat_id:int,db:Session = Depends(get_db), user: str = Depends(get_current_user)):
    chat = delete_chat(db,user,chat_id)
    if not chat:
        return ResponseSchema.fail(message="删除聊天失败",data=None)
    return ResponseSchema.ok(message="删除聊天成功",data=None)


# 被分享者取消分享
@router.get("/cancel_share/{share_id}",response_model=ResponseSchema)
async def cancel_share(share_id:int , user_id: str = Depends(get_current_user),db: Session = Depends(get_db)):
    chat_share = cancel_chat_share_api(db=db,chat_share_id=share_id,user_id=user_id)
    if not chat_share:
        return ResponseSchema.fail(message="取消失败",data=None)
    return ResponseSchema.ok(message="已取消分享",data=None)