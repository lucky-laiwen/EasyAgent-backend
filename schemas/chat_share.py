from pydantic import BaseModel, Field , field_serializer
from datetime import datetime

# 创建聊天
class CreateChatShare(BaseModel):
    owner_id: int = Field(..., description="用户id")
    chat_id: int = Field(..., description="聊天id")
    permission: int = Field(1, description="权限")
    shared_to_id: int = Field(..., description="分享用户id")
    
    class Config:
        from_attributes = True

# 返回整个聊天
class ChatShare(BaseModel):
    id: int = Field(..., description="分享聊天id")
    chat_id: int = Field(..., description="聊天id")
    owner_id: int = Field(..., description="用户id")
    permission: int = Field(1, description="权限")
    shared_to_id: int = Field(..., description="分享用户id")
    created_at:datetime = Field(..., description="创建时间")
    title:str | None = Field(None, description="聊天标题")
    class Config:
        from_attributes = True