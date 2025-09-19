from database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey ,func 
from sqlalchemy.orm import relationship
class Chat(Base):
    __tablename__ = 'chat'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    user_id = Column(Integer, ForeignKey('user.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),onupdate=func.now())

    # ✅ 反向关联
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")