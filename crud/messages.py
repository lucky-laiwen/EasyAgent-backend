from sqlalchemy.orm import Session

from models.user import User
from models.messages import Message
from models.chat import Chat
from typing import Optional

# 查询用户
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

# 创建聊天内容
def create_message(db: Session, chat_id: int, content: str ,sender: int, think_content: str,tool_content: str,tool_name: str) -> Optional[Message]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return None
    message = Message(chat_id=chat_id, content=content,sender=sender,think_content=think_content,tool_content=tool_content,tool_name=tool_name)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

# 查询聊天的详细内容
def get_chat_messages(db: Session, chat_id: int) -> Optional[Chat]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return None
    messages = chat.messages
    return list(messages)   