from pydantic import BaseModel, Field
from datetime import datetime
# 创建聊天
class CreateMessage(BaseModel):
    content: str = Field(..., description="聊天内容")
    sender:str = Field(..., description="聊天标题")
    
    class Config:
        from_attributes = True

# 返回聊天内容
class Message(BaseModel):
    id: int = Field(..., description="聊天id")
    content: str = Field(..., description="聊天内容")
    sender:int = Field(..., description="聊天标题")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True