from sqlalchemy.orm import Session
from typing import Optional
from models.chat import Chat
from models.user import User

# 查询用户是否存在
def get_user_by_id(db:Session,user_id:int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    return True

# 创建聊天
def create_chat(db:Session,user_id:int,id:int) -> Optional[Chat]:
    if not get_user_by_id(db,user_id):
        return None
    is_have_chat = db.query(Chat).filter(Chat.id == id,Chat.user_id == user_id).first()
    if not is_have_chat:
        chat = Chat(user_id=user_id,title=f"chat{id}")
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat
    else:
        return is_have_chat

# 获取对应用户的聊天记录
def get_chat_by_user_id(db:Session,user_id:int,page_size:int,last_id:int | None=None) -> Optional[list[Chat]]:
    if not get_user_by_id(db,user_id):
        return None
    query = db.query(Chat).filter(Chat.user_id == user_id)
    if last_id:
        query =query.filter(Chat.id < last_id)
    chats = query.order_by(Chat.id.desc()).limit(page_size).all()
    next_last_id = chats[-1].id if chats else None

    return {"data": chats, "next_last_id": next_last_id}