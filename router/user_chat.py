from fastapi import APIRouter, WebSocket, WebSocketDisconnect,Depends
from schemas.user_chat import SendUserChat,UserChat,historyUserChat,ChatMessage
from utils.utils import get_current_user
from crud.user_chat import send_user_message,get_chat_history,update_message_status_utils
from sqlalchemy.orm import Session
from database import get_db
from schemas.response import ResponseSchema
from datetime import datetime
from utils.connection_manager import manager
from database import SessionLocal
router = APIRouter(
    tags=["User Chat"],
    prefix="/user_chat"
)


def send_message_ws(receiver_id:int,content:str, user_id: int, db: Session):
    messages = send_user_message(db=db,receiver_id=receiver_id,sender_id=user_id,content=content)
    if not messages:
        return None
    messages_obj = UserChat.model_validate(messages)
    return messages_obj

def update_message_status(message_id:int,db: Session):
    message = update_message_status_utils(db,message_id)
    if not message:
        return None
    message_obj = UserChat.model_validate(message)
    return message_obj

# WebSocket 处理函数
@router.websocket("/ws/chat/{user_id}")
async def chat_ws(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("messageId", None):
                with SessionLocal() as db:
                    result = update_message_status(data['messageId'],db=db)
                if result:
                    # 获取返回的字典并转换 datetime 字段
                    message_dict = result.model_dump()

                    # 将 datetime 类型字段转换为 ISO 字符串
                    for key, value in message_dict.items():
                        if isinstance(value, datetime):
                            message_dict[key] = value.isoformat()
                    message_dict['type'] = 'update_message_status'
                    await manager.send_private_message(
                        to_user_id=data["to_user_id"],
                        message=message_dict  # 传递处理后的消息
                    )
                    await manager.send_private_message(
                        to_user_id=user_id,
                        message=message_dict  # 传递处理后的消息
                    )
                else:
                    manager.disconnect(user_id)
            else:
                with SessionLocal() as db:
                    provide = send_message_ws(data["to_user_id"], data["content"], user_id, db)
            
                if provide:
                    # 获取返回的字典并转换 datetime 字段
                    message_dict = provide.model_dump()

                    # 将 datetime 类型字段转换为 ISO 字符串
                    for key, value in message_dict.items():
                        if isinstance(value, datetime):
                            message_dict[key] = value.isoformat()

                    await manager.send_private_message(
                        to_user_id=data["to_user_id"],
                        message=message_dict  # 传递处理后的消息
                    )
                else:
                    manager.disconnect(user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)

@router.post("/send_message",response_model=ResponseSchema)
async def send_message(data:SendUserChat,token: str = Depends(get_current_user),db: Session = Depends(get_db)):
    messages = send_user_message(db=db,receiver_id=data.receiver_id,sender_id=token,content=data.content)
    if not messages:
        return ResponseSchema.fail(message="发送失败",data=None)
    messages_obj = UserChat.model_validate(messages)
    return ResponseSchema.ok(message="发送成功",data=messages_obj)

# 获取聊天记录
@router.get("/get_chat_history/{receiver_id}",response_model=ResponseSchema)
async def get_chat_history_api(receiver_id:int, token: str = Depends(get_current_user),db: Session = Depends(get_db)):
    chat_history = get_chat_history(db=db,user_id=token,receiver_id=receiver_id)
    if not chat_history:
        return ResponseSchema.fail(message="获取失败",data=None)
    chat_history_obj = [UserChat.model_validate(chat_message) for chat_message in chat_history]
    return ResponseSchema.ok(message="获取成功",data=chat_history_obj)
