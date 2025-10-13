from fastapi import APIRouter,Depends
from fastapi.responses import StreamingResponse
from utils.utils import get_current_user
from schemas.chat import CreateChat , ChatItem
from schemas.messages import Message
from crud.chat import create_chat,get_chat_by_user_id,update_chat_title,delete_chat
from crud.messages import create_message,get_chat_messages
from schemas.response import ResponseSchema
from database import get_db
from sqlalchemy.orm import Session
from utils.ollama import chat_with_ollama_stream,generate_chat_title
import json
import re
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

# 创建新聊天
@router.post('/create_chat', response_model=ResponseSchema)
async def create_chat_router(chatData: CreateChat, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    
    # 创建聊天对象
    chat_obj = create_chat(db, user, chatData.id)
    if not chat_obj:
        return ResponseSchema.fail(message="创建聊天失败", data=None)

    # 存用户发的消息
    message_obj = create_message(db, chat_obj.id, chatData.message, 0, think_content="")
    message_out = Message.model_validate(message_obj)
    return ResponseSchema.ok(message="创建聊天成功", data=message_out)


# 创建聊天
@router.post("/stream")
async def create_chat_router(
    chatData: CreateChat,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    chat_obj = create_chat(db, user, chatData.id)
    chat_id = chat_obj.id

    message_obj = get_chat_messages(db, chat_id)
    chat_message_list = [Message.model_validate(message) for message in message_obj]

    messages_for_llm = [
        {"role": "user" if msg.sender == 0 else "assistant", "content": msg.content}
        for msg in chat_message_list
    ]

    formal_content = ""
    think_content = ""

    async def event_generator():
        nonlocal formal_content, think_content

        for chunk in chat_with_ollama_stream(messages_for_llm):
            if not chunk:
                continue

            thinking = chunk.get("thinking")
            content = chunk.get("content")

            if thinking is not None:
                think_content += thinking
                yield f"data: {json.dumps({'content': thinking, 'type': 'think'})}\n\n"

            elif content is not None:
                formal_content += content
                yield f"data: {json.dumps({'content': content, 'type': 'text'})}\n\n"

        # ✅ 输出 done 事件
        yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"

        # ✅ 保存完整内容
        create_message(db, chat_id, formal_content, 1, think_content)

    return StreamingResponse(event_generator(), media_type="text/event-stream")




# 查询对应用户的所有聊天
@router.get('/get_chat_list',response_model=ResponseSchema)
async def get_chat_list_router(db:Session = Depends(get_db), user: str = Depends(get_current_user),page_size:int=200,last_id:int|None=None):
    user_id = user
    chat_list =get_chat_by_user_id(db,user_id,page_size,last_id)
    if not chat_list:
        return ResponseSchema.fail(message="查询聊天列表失败",data=None)
    chat_list_out = [ChatItem.model_validate(chat) for chat in chat_list["data"]]
    return ResponseSchema.ok(message="查询聊天列表成功",data={"chat_list":chat_list_out,"next_last_id":chat_list["next_last_id"]})

@router.get('/get_chat_message/{chat_id}',response_model=ResponseSchema)
async def get_chat_message_router(chat_id:int,db:Session = Depends(get_db), _: str = Depends(get_current_user)):
    chat_obj = get_chat_messages(db,chat_id)
    chat_out = [Message.model_validate(message) for message in chat_obj]
    return ResponseSchema.ok(message="查询聊天消息成功",data=chat_out)

# 获取聊天标题
@router.post('/get_chat_title',response_model=ResponseSchema)
async def get_chat_title_router(chatData: CreateChat, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    # 调用 AI 生成标题
    title = generate_chat_title(chatData.message)
    chat_msg = update_chat_title(db,user,chatData.id,title)
    if not chat_msg:
        return ResponseSchema.fail(message="获取聊天标题失败",data=None)
    
    return ResponseSchema.ok(message="获取聊天标题成功",data=title)

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