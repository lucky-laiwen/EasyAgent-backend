from sqlalchemy.orm import Session
from models.chat_attachment import ChatAttachment
from typing import Optional, List


def create_attachment(
    db: Session,
    chat_id: int,
    filename: str,
    file_type: str,
    file_size: int,
    minio_key: str,
    file_url: str = None,
    text_content: str = None,
) -> ChatAttachment:
    attachment = ChatAttachment(
        chat_id=chat_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        minio_key=minio_key,
        file_url=file_url,
        text_content=text_content,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def bind_attachments_to_message(db: Session, file_ids: list, chat_id: int, message_id: int):
    """将附件绑定到指定消息和聊天"""
    attachments = db.query(ChatAttachment).filter(ChatAttachment.id.in_(file_ids)).all()
    for att in attachments:
        att.chat_id = chat_id
        att.message_id = message_id
    db.commit()


def get_attachments_by_ids(db: Session, file_ids: List[int]) -> List[ChatAttachment]:
    return db.query(ChatAttachment).filter(ChatAttachment.id.in_(file_ids)).all()


def get_attachment_by_id(db: Session, file_id: int) -> Optional[ChatAttachment]:
    return db.query(ChatAttachment).filter(ChatAttachment.id == file_id).first()


def delete_attachments_by_chat(db: Session, chat_id: int) -> int:
    count = db.query(ChatAttachment).filter(ChatAttachment.chat_id == chat_id).delete()
    db.commit()
    return count
