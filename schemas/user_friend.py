from pydantic import BaseModel
from datetime import datetime
from typing import Optional
class UserFriend(BaseModel):
    id:int
    user_id:int
    friend_id:int
    status:int
    created_at:datetime

    class Config:
        from_attributes = True

class get_user_friends(BaseModel):
    user_id:int
    friend_id:int
    status:int

class UserInfoOut(BaseModel):
    id: int
    name: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True

class UserFriendOut(BaseModel):
    id: int
    status: int
    created_at: datetime
    friend: UserInfoOut  # 嵌套 friend 信息

    class Config:
        from_attributes = True

class AddFriendSchema(BaseModel):
    friend_id: int