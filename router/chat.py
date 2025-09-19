from fastapi import APIRouter,Depends
from fastapi.responses import StreamingResponse
from utils.utils import get_current_user
from schemas.chat import CreateChat , ChatItem
from schemas.messages import Message
from crud.chat import create_chat,get_chat_by_user_id
from crud.messages import create_message,get_chat_messages
from schemas.response import ResponseSchema
from database import get_db
from sqlalchemy.orm import Session
from utils.ollama import chat_with_ollama_stream
import json
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

# 创建聊天
@router.post('/create_chat')
async def create_chat_router(
    chatData: CreateChat,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    # 1. 创建聊天对象
    chat_obj = create_chat(db, user, chatData.id)
    chat_id = chat_obj.id
    if not chat_obj:
        return ResponseSchema.fail(message="创建聊天失败", data=None)

    # 先存用户消息
    create_message(db, chat_obj.id, chatData.message, 0)
    message_obj = get_chat_messages(db,chat_id)
    chat_message_list = [Message.model_validate(message) for message in message_obj]
    messages_for_llm = [
    {"role": "user" if msg.sender == 0 else "assistant", "content": msg.content}
    for msg in chat_message_list
    ]   
    # 2. 定义一个变量收集完整 AI 回复
    full_resp = ""

    async def event_generator():
        nonlocal full_resp
        for chunk in chat_with_ollama_stream(messages_for_llm):
            full_resp += chunk  # 累积完整回复
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        # 生成结束事件
        yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"

        # 3. 在生成完毕后，保存完整消息到数据库
        create_message(db, chat_id, full_resp, 1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")




# 查询对应用户的所有聊天
@router.get('/get_chat_list',response_model=ResponseSchema)
async def get_chat_list_router(db:Session = Depends(get_db), user: str = Depends(get_current_user),page_size:int=20,last_id:int|None=None):
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