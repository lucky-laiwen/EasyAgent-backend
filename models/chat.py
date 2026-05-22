from database import Base
from sqlalchemy import Column, Integer, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
class Chat(Base):
    __tablename__ = 'chat'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),onupdate=func.now())
    kb_id = Column(Integer, ForeignKey('knowledge_base.id', ondelete='SET NULL'), nullable=True)

    # ✅ 反向关联
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    shares = relationship("ChatShare", back_populates="chat", cascade="all, delete-orphan")
    attachments = relationship("ChatAttachment", back_populates="chat", cascade="all, delete-orphan")