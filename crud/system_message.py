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
    source_id: int | None = None,
    sender_title: str | None = None,
    sender_content: str | None = None,
) -> tuple[SystemMessage, SystemMessage | None]:
    # 接收人的记录
    receiver_msg = SystemMessage(
        title=title,
        content=content,
        user_id=user_id,
        source_id=source_id,
        action_type=action_type
    )
    db.add(receiver_msg)

    # 发起人的记录
    sender_msg = None
    if sender_title or sender_content:
        sender_msg = SystemMessage(
            title=sender_title,
            content=sender_content,
            user_id=source_id,
            source_id=user_id,
            action_type=2
        )
        db.add(sender_msg)

    db.commit()
    db.refresh(receiver_msg)
    if sender_msg:
        db.refresh(sender_msg)
    return receiver_msg, sender_msg


def update_system_message_status(
    db: Session,
    receiver_id: int,
    sender_id: int,
    action_type: int = 0,
    receiver_title: str | None = None, 
    receiver_content: str | None = None, 
    sender_title: str | None = None, 
    sender_content: str | None = None, 
):
    receiver_msg = db.query(SystemMessage).filter(SystemMessage.user_id == receiver_id, SystemMessage.source_id == sender_id).first()
    sender_msg = db.query(SystemMessage).filter(SystemMessage.user_id == sender_id, SystemMessage.source_id == receiver_id).first()
    if receiver_msg:
        receiver_msg.is_read = 1
        receiver_msg.title = receiver_title
        receiver_msg.content = receiver_content
        receiver_msg.action_type = action_type
        db.commit()
        db.refresh(receiver_msg)
    if sender_msg:
        sender_msg.is_read = 1
        sender_msg.title = sender_title
        sender_msg.content = sender_content
        sender_msg.action_type = action_type
        db.commit()
        db.refresh(sender_msg)
    return receiver_msg, sender_msg