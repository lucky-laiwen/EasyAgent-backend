from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from database import Base
from models.chat_message import ChatMessage
class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    is_active = Column(Integer, default=0)
    avatar = Column(Text, default='https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Chat 的关系
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")

    # ChatMessage 的关系，使用字符串延迟绑定
    sent_messages = relationship(
        "ChatMessage",
        foreign_keys=ChatMessage.sender_id,
        back_populates="sender",
        cascade="all, delete-orphan"
    )

    received_messages = relationship(
        "ChatMessage",
        foreign_keys=ChatMessage.receiver_id,
        back_populates="receiver",
        cascade="all, delete-orphan"
    )

    
