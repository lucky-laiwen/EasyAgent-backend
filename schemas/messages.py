from pydantic import BaseModel, Field,Json
from datetime import datetime
from typing import Optional
# 创建聊天
class CreateMessage(BaseModel):
    content: str = Field(..., description="聊天内容")
    sender:str = Field(..., description="聊天标题")
    
    class Config:
        from_attributes = True

# 返回聊天内容
class Message(BaseModel):
    id: int = Field(..., description="聊天信息id")
    content: str = Field(..., description="聊天内容")
    sender:int = Field(..., description="聊天标题")
    created_at: datetime = Field(..., description="创建时间")
    chat_id: int = Field(..., description="聊天id")
    think_content: str = Field(..., description="思考内容")
    tool_content: Optional[Json] = Field(None, description="工具内容")
    tool_name: Optional[str] = Field(None, description="工具名称")
    
    class Config:
        from_attributes = True