from database import Base
from sqlalchemy import Column, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

class ChatShare(Base):
    __tablename__ = 'chat_share'
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey('chat.id', ondelete='CASCADE'), nullable=False)
    owner_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    shared_to_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    permission = Column(Integer, default=1)  # 权限：1只读 2可编辑
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系 - 使用字符串形式避免循环导入
    chat = relationship("Chat", back_populates="shares")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_shares")
    shared_to_user = relationship("User", foreign_keys=[shared_to_id], back_populates="share_received")