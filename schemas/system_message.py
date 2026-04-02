from pydantic import BaseModel, Field , field_serializer
from datetime import datetime
# 创建聊天
class SystemMessage(BaseModel):
    id : int = Field(...,description="系统消息id")
    user_id : int = Field(...,description="用户id")
    source_id : int | None = Field(None,description="来源用户id")
    title : str = Field(...,description="系统消息标题")
    content : str = Field(...,description="系统消息内容")
    is_read : int = Field(0,description="是否已读")
    created_at : datetime = Field(...,description="创建时间")
    action_type : int = Field(...,description="系统消息类型")
    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime, _info):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    
    class Config:
        from_attributes = True