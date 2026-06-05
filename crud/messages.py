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
def create_message(db: Session, chat_id: int, content: str, sender: int, think_content: str = None, message_type: str = None, rag_references=None) -> Optional[Message]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return None
    message = Message(
        chat_id=chat_id,
        content=content,
        sender=sender,
        think_content=think_content,
        message_type=message_type,
        rag_references=rag_references
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
        tool_input=tool_input,
        status=2
    )
    db.add(tool_call)
    db.commit()
    db.refresh(tool_call)
    return tool_call


# 更新工具消息内容（标记为完成）
def update_tool_message(db: Session, tool_call_id: int, tool_content: str) -> Optional[ToolCall]:
    tool_call = db.query(ToolCall).filter(ToolCall.id == tool_call_id).first()
    if not tool_call:
        return None
    tool_call.tool_content = tool_content
    tool_call.status = 1
    db.commit()
    db.refresh(tool_call)
    return tool_call


# 增量更新工具内容（不改变状态，用于 PPT 增量保存）
def update_tool_content(db: Session, tool_call_id: int, tool_content: str) -> Optional[ToolCall]:
    tool_call = db.query(ToolCall).filter(ToolCall.id == tool_call_id).first()
    if not tool_call:
        return None
    tool_call.tool_content = tool_content
    db.commit()
    db.refresh(tool_call)
    return tool_call


# 更新消息内容
def update_message_content(db: Session, message_id: int, content: str, think_content: str = None, rag_references=None) -> Optional[Message]:
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        return None
    message.content = content
    if think_content is not None:
        message.think_content = think_content
    if rag_references is not None:
        message.rag_references = rag_references
    db.commit()
    db.refresh(message)
    return message


# 查询单个工具调用
def get_tool_call_by_id(db: Session, tool_call_id: int) -> Optional[ToolCall]:
    return db.query(ToolCall).filter(ToolCall.id == tool_call_id).first()


# 查询聊天的详细内容
def get_chat_messages(db: Session, chat_id: int) -> List[Message]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return []
    return list(chat.messages)


# 按 message_id 和 tool_name 查询工具调用记录
def get_tool_call_by_message_and_name(db: Session, message_id: int, tool_name: str) -> Optional[ToolCall]:
    return db.query(ToolCall).filter(
        ToolCall.message_id == message_id,
        ToolCall.tool_name == tool_name
    ).first()


# 查询单条消息
def get_message_by_id(db: Session, message_id: int) -> Optional[Message]:
    return db.query(Message).filter(Message.id == message_id).first()


# 删除消息关联的工具调用记录（可选保留指定类型）
def delete_tool_calls_by_message(db: Session, message_id: int, exclude_tool_name: str = None):
    query = db.query(ToolCall).filter(ToolCall.message_id == message_id)
    if exclude_tool_name:
        query = query.filter(ToolCall.tool_name != exclude_tool_name)
    tool_calls = query.all()
    for tc in tool_calls:
        db.delete(tc)
    db.commit()


# 重置大纲状态用于重新生成
def reset_outline_for_regenerate(db: Session, outline_tool_id: int) -> Optional[ToolCall]:
    tool_call = db.query(ToolCall).filter(ToolCall.id == outline_tool_id).first()
    if not tool_call:
        return None
    tool_call.status = 2
    tool_call.tool_content = None
    db.commit()
    db.refresh(tool_call)
    return tool_call