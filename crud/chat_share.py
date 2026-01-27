from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.chat_share import ChatShare
from models.chat import Chat
from models.user import User
from typing import Optional

def get_user_by_id(db:Session,user_id:int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    return True

# 创建聊天分享
def create_chat_share(db: Session, owner_id: int, chat_id: int, permission: int, shared_to_id: int) -> Optional[ChatShare]:
    # 检查用户是否存在
    if not get_user_by_id(db, owner_id):
        return None
    if not get_user_by_id(db, shared_to_id):
        return None

    # 检查是否已经分享给特定用户
    # 而不是检查是否有任何人分享过这个聊天
    existing_share = db.query(ChatShare).filter(
        ChatShare.chat_id == chat_id,
        ChatShare.shared_to_id == shared_to_id  # 检查是否已分享给目标用户
    ).first()
    
    if existing_share:
        return None  # 已经分享给这个用户了
    
    # 添加聊天分享
    chat_share = ChatShare(owner_id=owner_id, chat_id=chat_id, permission=permission, shared_to_id=shared_to_id)
    db.add(chat_share)
    db.commit()
    db.refresh(chat_share)
    return chat_share

# 同意接受此聊天记录
def accept_chat_share_api(db: Session, chat_share_id: int):
    chat_share = db.query(ChatShare).filter(ChatShare.id == chat_share_id).first()
    if not chat_share:
        return None
    chat_share.permission = 2  # 更新权限为接受
    db.commit()
    db.refresh(chat_share)
    return chat_share

# 被分享者取消分享
def cancel_chat_share_api(db: Session, chat_share_id: int,user_id:int):
    chat_share = db.query(ChatShare).filter(and_(
        ChatShare.chat_id == chat_share_id,
        ChatShare.shared_to_id == user_id
    )).first()
    if not chat_share:
        return None
    chat_share.permission = 1
    db.commit()
    db.refresh(chat_share)
    return chat_share

# 查询聊天分享记录
def get_chat_share_api(db: Session, chat_share_id: int) -> Optional[ChatShare]:
    chat_share = db.query(ChatShare).filter(ChatShare.chat_id == chat_share_id).first()
    if not chat_share:
        return None
    return chat_share