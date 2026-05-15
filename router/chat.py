from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from utils.utils import get_current_user
from schemas.chat import CreateChat, ChatItem, AllChatItem
from schemas.messages import Message, ToolCall
from crud.chat import create_chat, get_chat_by_user_id, update_chat_title, delete_chat
from crud.messages import create_message, get_chat_messages, add_tool_call, update_tool_message, get_tool_call_by_id, update_message_content
from crud.chat_share import cancel_chat_share_api
from schemas.response import ResponseSchema
from database import get_db
from sqlalchemy.orm import Session
import json
from utils.openai_client import chat_stream, generate_chat_title
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

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
    create_message(db, chatData.get("id"), chatData.get("message"), 0,None)
    message_obj = get_chat_messages(db, chatData.get("id"))
    message_out = [Message.model_validate(m) for m in message_obj]
    messages_for_llm = [
        {"role": "user" if msg.sender == 0 else "assistant", "content": msg.content }
        for msg in message_out
    ]
    # 预创建 AI 消息占位，tool_call 将关联到此消息
    ai_msg = create_message(db, chatData.get("id"), "", 1, None)
    if not ai_msg:
        return ResponseSchema.fail(message="创建AI消息失败",data=None)
    ai_msg_out = Message.model_validate(ai_msg)
    formal_content = ""
    think_content = ""
    tool_calls_data = []  # 存储多个工具调用
    tool_call_map = {}  # tool_run_id -> ToolCall db对象，用于匹配并行工具调用

    async def event_generator():
        nonlocal formal_content, think_content, tool_calls_data, tool_call_map
        try:
            async for chunk in chat_stream(messages_for_llm):
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
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        # 更新 AI 消息内容
        update_message_content(db, ai_msg.id, formal_content, think_content)
                
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