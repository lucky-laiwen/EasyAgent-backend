from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models.chat_message import ChatMessage

# 发送信息
def send_user_message(db:Session,receiver_id:int,sender_id:int,content:str):
    chat_message = ChatMessage(sender_id=sender_id,receiver_id=receiver_id,content=content)
    db.add(chat_message)
    db.commit() 
    db.refresh(chat_message)
    return chat_message

# 获取聊天记录
def get_chat_history(db:Session,user_id:int,receiver_id:int):
    chat_messages = (
    db.query(ChatMessage)
    .filter(
        or_(
            and_(
                ChatMessage.sender_id == user_id,
                ChatMessage.receiver_id == receiver_id
            ),
            and_(
                ChatMessage.sender_id == receiver_id,
                ChatMessage.receiver_id == user_id
            )
        )
    )
    .order_by(ChatMessage.created_at.asc())
    .all()
)
    return chat_messages

# 更改消息已读未读状态
def update_message_status_utils(db: Session, message_id: int):
    chat_message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not chat_message:
        return None
    chat_message.status = 1
    db.commit()
    db.refresh(chat_message)
    return chat_message

# 查询所有未读消息
def get_unread_messages_utils(db: Session, user_id: int):
    chat_messages = (
    db.query(ChatMessage)
        .filter(
            and_(
                ChatMessage.receiver_id == user_id,
                ChatMessage.status == 0
            )
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return chat_messages

# 查询所有用户接收到的消息
def get_all_messages_utils(db: Session, user_id: int):
    chat_messages = (
    db.query(ChatMessage)
        .filter(
            or_(
                ChatMessage.receiver_id == user_id,
                ChatMessage.sender_id == user_id
            )
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return chat_messages