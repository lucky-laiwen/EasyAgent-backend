from sqlalchemy import Column, BigInteger, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base


class ChatAttachment(Base):
    __tablename__ = "chat_attachment"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    chat_id = Column(Integer, ForeignKey("chat.id", ondelete="CASCADE"), nullable=True)
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    minio_key = Column(String(500), nullable=False)
    file_url = Column(String(1000), nullable=True)
    text_content = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    chat = relationship("Chat", back_populates="attachments")
    message = relationship("Message", back_populates="attachments")
