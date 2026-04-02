from sqlalchemy.orm import Session
from models.system_message import SystemMessage
# 获取系统消息
def get_system_messages_by_user_id(db: Session, user_id: int):
    return db.query(SystemMessage).filter(SystemMessage.user_id == user_id).all()

# 创建系统消息
def create_system_message(
    db: Session,
    title: str,
    content: str,
    user_id: int,
    action_type: int = 0,
    source_id: int | None = None
) -> SystemMessage:
    system_message = SystemMessage(
        title=title,
        content=content,
        user_id=user_id,
        action_type=action_type,
        source_id=source_id
    )
    db.add(system_message)
    db.commit()
    db.refresh(system_message)
    return system_message


def update_system_message_status(db: Session, message_id: int,title: str,content: str,action_type: int):
    system_message = db.query(SystemMessage).filter(SystemMessage.id == message_id).first()
    if system_message:
        system_message.is_read = 1
        system_message.title = title
        system_message.content = content
        system_message.action_type = action_type
        db.commit()
        db.refresh(system_message)
        return system_message
    return None