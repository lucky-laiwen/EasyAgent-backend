from sqlalchemy import Column, BigInteger, Integer, Text, ForeignKey, DateTime, func, String
from sqlalchemy.orm import relationship
from database import Base


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(100), nullable=False, comment="工具名称")
    tool_content = Column(Text, nullable=True, comment="工具返回结果")
    tool_input = Column(Text, nullable=True, comment="工具输入参数")
    status = Column(Integer, default=1, comment="状态: 1=成功, 0=失败")
    created_at = Column(DateTime, server_default=func.now())

    # 关系映射
    message = relationship("Message", back_populates="tool_calls")
