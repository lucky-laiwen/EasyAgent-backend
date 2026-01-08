from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# 用于创建用户的请求参数
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


# 用于返回给客户端的数据
class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    avatar:str
    class Config:
        from_attributes = True


# 当前User
class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime
    password: str

    class Config:
        from_attributes = True

# 登录规范
class LoginSchema(BaseModel):
    token: str
    user: UserOut

# 更新用户资料
class UserUpdate(BaseModel):
    name: str
    email: str
    avatar: Optional[str] = None
