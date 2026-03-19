from database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey ,func ,Text
from sqlalchemy.orm import relationship
class Chat(Base):
    __tablename__ = 'chat'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(Text))
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),onupdate=func.now())

    # ✅ 反向关联
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    shares = relationship("ChatShare", back_populates="chat", cascade="all, delete-orphan")