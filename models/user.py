from sqlalchemy import Column, Integer, String, DateTime, func
from database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    password = Column(String, nullable=False)
    is_active = Column(Integer, default=0)

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")