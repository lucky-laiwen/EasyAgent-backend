from sqlalchemy.orm import Session

from models.user import User
from models.messages import Message
from models.chat import Chat
from models.tool_call import ToolCall
from typing import Optional, List


# 查询用户
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


# 创建聊天内容
def create_message(db: Session, chat_id: int, content: str, sender: int, think_content: str = None) -> Optional[Message]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return None
    message = Message(
        chat_id=chat_id,
        content=content,
        sender=sender,
        think_content=think_content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


# 添加工具调用记录
def add_tool_call(db: Session, message_id: int, tool_name: str, tool_content: str = None, tool_input: str = None) -> ToolCall:
    tool_call = ToolCall(
        message_id=message_id,
        tool_name=tool_name,
        tool_content=tool_content,
        tool_input=tool_input
    )
    db.add(tool_call)
    db.commit()
    db.refresh(tool_call)
    return tool_call


# 更新工具消息内容
def update_tool_message(db: Session, tool_call_id: int, tool_content: str) -> Optional[ToolCall]:
    tool_call = db.query(ToolCall).filter(ToolCall.id == tool_call_id).first()
    if not tool_call:
        return None
    tool_call.tool_content = tool_content
    db.commit()
    db.refresh(tool_call)
    return tool_call


# 查询单个工具调用
def get_tool_call_by_id(db: Session, tool_call_id: int) -> Optional[ToolCall]:
    return db.query(ToolCall).filter(ToolCall.id == tool_call_id).first()


# 查询聊天的详细内容
def get_chat_messages(db: Session, chat_id: int) -> List[Message]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return []
    return list(chat.messages)   