from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# 工具调用响应
class ToolCall(BaseModel):
    id: int = Field(..., description="工具调用ID")
    tool_name: str = Field(..., description="工具名称")
    tool_content: Optional[str] = Field(None, description="工具返回结果")
    tool_input: Optional[str] = Field(None, description="工具输入参数")
    status: int = Field(1, description="状态: 1=成功, 0=失败")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


# 创建聊天
class CreateMessage(BaseModel):
    content: str = Field(..., description="聊天内容")
    sender: str = Field(..., description="聊天标题")

    class Config:
        from_attributes = True


# 返回聊天内容
class Message(BaseModel):
    id: int = Field(..., description="聊天信息id")
    content: str = Field(..., description="聊天内容")
    sender: int = Field(..., description="发送方: 0=user, 1=ai")
    created_at: datetime = Field(..., description="创建时间")
    chat_id: int = Field(..., description="聊天id")
    think_content: Optional[str] = Field(None, description="思考内容")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="工具调用列表")

    class Config:
        from_attributes = True