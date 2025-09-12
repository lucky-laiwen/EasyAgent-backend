from pydantic import BaseModel, Field
from typing import List, Optional

# 创建聊天
class CreateChat(BaseModel):
    user_id: int = Field(..., description="用户id")
    message: str = Field(..., description="聊天内容")
    title:str = Field(..., description="聊天标题")

# 删除聊天
class DeleteChat(BaseModel):
    chat_id: int = Field(..., description="聊天id")
    user_id: int = Field(..., description="用户id")

# 获取聊天列表
class GetChatList(BaseModel):
    user_id: int = Field(..., description="用户id")
    page: int = Field(1, description="页码")
    page_size: int = Field(10, description="每页数量")

# 获取聊天详情
class GetChatDetail(BaseModel):
    chat_id: int = Field(..., description="聊天id")
    user_id: int = Field(..., description="用户id")
