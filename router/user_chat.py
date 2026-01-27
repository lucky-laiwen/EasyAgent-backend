from fastapi import APIRouter, WebSocket, WebSocketDisconnect,Depends
from schemas.chat_share import ChatShare
from schemas.user_chat import SendUserChat,UserChat,historyUserChat,ChatMessage
from utils.utils import get_current_user
from crud.user_chat import send_user_message,get_chat_history,update_message_status_utils,get_unread_messages_utils,get_all_messages_utils,update_chat_share_id
from crud.chat_share import create_chat_share,accept_chat_share_api,get_chat_share_api
from sqlalchemy.orm import Session
from database import get_db
from schemas.response import ResponseSchema
from datetime import datetime
from utils.connection_manager import manager
from database import SessionLocal
from crud.chat import get_chat_by_id
from schemas.chat import ChatItem
router = APIRouter(
    tags=["User Chat"],
    prefix="/user_chat"
)


def send_message_ws(receiver_id:int,content:str, user_id: int, db: Session,chat_id: int | None = None):
    messages = send_user_message(db=db,receiver_id=receiver_id,sender_id=user_id,content=content,share_chat_id=chat_id)
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

def create_chat_share_utils(db: Session, user_id: int, chat_id: int, permission: int, shared_to_id: int):
    chat_share = create_chat_share(db, user_id, chat_id, permission, shared_to_id)
    if not chat_share:
        return None
    chat_share_obj = ChatShare.model_validate(chat_share)
    return chat_share_obj

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
                    chat_share = None
                    provide = send_message_ws(data["to_user_id"], data["content"], user_id, db, data.get("chatId", None))
                    
                    if data.get("chatId", None):
                        
                        chat_share = create_chat_share_utils(db, user_id, data["chatId"], 1, data["to_user_id"])
                            
                        # 检查是否因重复而出现问题
                        if not chat_share:
                            # 发送错误消息但不中断连接
                            error_message = {
                                "type": "error",
                                "message": "您已分享过此消息",
                                "error_code": "DUPLICATE_SHARE"
                            }
                            await manager.send_private_message(
                                to_user_id=user_id,
                                message=error_message
                            )
                            # 继续执行，不要 return
                            chat_share = None  # 确保 chat_share 为 None
    
                    if provide:
                        # 获取返回的字典并转换 datetime 字段
                        message_dict = provide.model_dump()
                        
                        if chat_share:
                            chat_share_dict = chat_share.model_dump()
                            chat_share_dict['title'] = data["title"]
                            for key, value in chat_share_dict.items():
                                if isinstance(value, datetime):
                                    chat_share_dict[key] = value.isoformat()
                            message_dict['share_chat'] = chat_share_dict

                        # 将 datetime 类型字段转换为 ISO 字符串
                        for key, value in message_dict.items():
                            if isinstance(value, datetime):
                                message_dict[key] = value.isoformat()

                        await manager.send_private_message(
                            to_user_id=data["to_user_id"],
                            message=message_dict
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
    for chat_message in chat_history_obj:
        if chat_message.share_chat_id:
            share_msg = get_chat_share_api(db,chat_message.share_chat_id)
            if share_msg:
                chat_message.share_chat = ChatShare.model_validate(share_msg)
                chat_share = get_chat_by_id(db,chat_message.share_chat_id)
                if chat_share:
                    chat_share_obj = ChatItem.model_validate(chat_share)
                    chat_message.share_chat.title = chat_share_obj.title
            else:
                update_chat_share_id(db=db,chat_id=chat_message.id)
    return ResponseSchema.ok(message="获取成功",data=chat_history_obj)

# 查询所有未读消息
@router.get("/get_unread_messages",response_model=ResponseSchema)
async def get_unread_messages(token: str = Depends(get_current_user),db: Session = Depends(get_db)):
    unread_messages = get_unread_messages_utils(db=db,user_id=token)
    if not unread_messages:
        return ResponseSchema.fail(message="获取失败",data=None)
    unread_messages_obj = [UserChat.model_validate(unread_message) for unread_message in unread_messages]
    return ResponseSchema.ok(message="获取成功",data=unread_messages_obj)

# 查询全部用户接收到的消息
@router.get("/get_all_messages",response_model=ResponseSchema)
async def get_all_messages(token: str = Depends(get_current_user),db: Session = Depends(get_db)):
    
    all_messages = get_all_messages_utils(db=db,user_id=token)
    if not all_messages:    
        return ResponseSchema.fail(message="获取失败",data=None)
    all_messages_obj = [UserChat.model_validate(all_message) for all_message in all_messages]
    return ResponseSchema.ok(message="获取成功",data=all_messages_obj)

# 接受分享
@router.get("/accept_share/{share_id}",response_model=ResponseSchema)
async def accept_share(share_id:int , token: str = Depends(get_current_user),db: Session = Depends(get_db)):
    chat_share = accept_chat_share_api(db=db,chat_share_id=share_id)
    if not chat_share:    
        return ResponseSchema.fail(message="获取失败",data=None)
    print(chat_share,909090)
    return ResponseSchema.ok(message="已同意接受",data=None)

    