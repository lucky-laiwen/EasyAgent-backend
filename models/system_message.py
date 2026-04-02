from database import Base
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from models.user import User

class SystemMessage(Base):
    __tablename__ = "system_message"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
    )

    title: Mapped[str | None] = mapped_column(
        String(255)
    )

    content: Mapped[str | None] = mapped_column(
        Text
    )

    is_read: Mapped[int] = mapped_column(
        default=0
    )

    action_type: Mapped[int | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # 反向关联
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="system_messages"
    )

    source_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[source_id],
        back_populates="source_system_messages"
    )
