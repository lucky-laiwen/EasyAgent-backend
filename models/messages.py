from sqlalchemy import Column, BigInteger, Integer, Text, ForeignKey, DateTime, func, SmallInteger
from sqlalchemy.orm import relationship
from database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    chat_id = Column(Integer, ForeignKey("chat.id", ondelete="CASCADE"), nullable=False)
    sender = Column(SmallInteger, nullable=False, comment="0=user, 1=ai")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # 关系映射，方便 ORM 查询时直接获取 chat
    chat = relationship("Chat", back_populates="messages")
