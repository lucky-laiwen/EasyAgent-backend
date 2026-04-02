from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

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

    # ChatMessage 的关系 - 需要添加级联删除
    sent_messages = relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )

    received_messages = relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )

    # ChatShare 的关系 - 需要添加级联删除
    owned_shares = relationship("ChatShare", foreign_keys="ChatShare.owner_id", 
                              back_populates="owner", cascade="all, delete-orphan")
    share_received = relationship("ChatShare", foreign_keys="ChatShare.shared_to_id", 
                                back_populates="shared_to_user", cascade="all, delete-orphan")

    # UserFriend 关系 - 可能需要考虑
    sent_friend_requests = relationship(
        "UserFriend", 
        foreign_keys="UserFriend.user_id", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    received_friend_requests = relationship(
        "UserFriend", 
        foreign_keys="UserFriend.friend_id", 
        back_populates="friend", 
        cascade="all, delete-orphan"
    )

    # SystemMessage 的关系（接收方）
    system_messages = relationship(
        "SystemMessage",
        foreign_keys="SystemMessage.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # SystemMessage 的关系（来源方）
    source_system_messages = relationship(
        "SystemMessage",
        foreign_keys="SystemMessage.source_id",
        back_populates="source_user"
    )