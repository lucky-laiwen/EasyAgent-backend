from pydantic import BaseModel, Field , field_serializer
from datetime import datetime
# 创建聊天
class CreateChat(BaseModel):
    message: str = Field(..., description="聊天内容")
    title:str = Field(..., description="聊天标题")

    class Config:
        from_attributes = True

# 聊天详情返回
class ChatItem(BaseModel):
    id: int = Field(..., description="聊天id")
    message: str = Field(..., description="聊天内容")
    title:str = Field(..., description="聊天标题")
    created_at:datetime = Field(..., description="创建时间")
    class Config:
        from_attributes = True
    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime, _info):
        return value.strftime("%Y-%m-%d %H:%M:%S")

# 删除聊天
class DeleteChat(BaseModel):
    chat_id: int = Field(..., description="聊天id")
    user_id: int = Field(..., description="用户id")

# 获取聊天列表
class GetChatList(BaseModel):
    page: int = Field(1, description="页码")
    page_size: int = Field(10, description="每页数量")

# 获取聊天详情
class GetChatDetail(BaseModel):
    chat_id: int = Field(..., description="聊天id")
    user_id: int = Field(..., description="用户id")
