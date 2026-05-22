from database import Base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship


class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), default='')
    chroma_collection = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    documents = relationship("KnowledgeDocument", back_populates="knowledge_base", cascade="all, delete-orphan")


class KnowledgeDocument(Base):
    __tablename__ = 'knowledge_document'

    id = Column(Integer, primary_key=True, index=True)
    kb_id = Column(Integer, ForeignKey('knowledge_base.id', ondelete='CASCADE'), nullable=False)
    chat_id = Column(Integer, ForeignKey('chat.id', ondelete='CASCADE'), nullable=True, comment="NULL=全局文档, 非NULL=会话专属文档")
    message_id = Column(BigInteger, ForeignKey('messages.id', ondelete='CASCADE'), nullable=True, comment="NULL=未绑定消息, 非NULL=绑定到具体消息")
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default='processing')  # processing / completed / failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
