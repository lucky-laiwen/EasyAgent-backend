from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from schemas.chat_share import ChatShare
class UserChat(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content:str
    status: int
    created_at: datetime
    updated_at: datetime
    share_chat_id: Optional[int] = None
    share_chat: ChatShare | None = None
    class Config:
        from_attributes = True

class SendUserChat(BaseModel):
    receiver_id: int
    content:str

class historyUserChat(BaseModel):
    sender_id: int
    receiver_id: int

class ChatMessage(BaseModel):
    user_id: int
    username: str
    content: str
    timestamp: datetime | None = None
