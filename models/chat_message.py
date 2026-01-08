from sqlalchemy import Column, BigInteger, Integer, Text, SmallInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base

class ChatMessage(Base):
    __tablename__ = 'chat_message'

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(SmallInteger, default=0, comment='0=未读,1=已读')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 这里不直接导入 User，使用字符串形式
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")
