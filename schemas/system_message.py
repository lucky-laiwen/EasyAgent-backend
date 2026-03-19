from pydantic import BaseModel, Field , field_serializer
from datetime import datetime
# 创建聊天
class SystemMessage(BaseModel):
    id = Field(...,description="系统消息id")
    user_id = Field(...,description="用户id")
    title = Field(...,description="系统消息标题")
    content = Field(...,description="系统消息内容")
    is_read = Field(0,description="是否已读")
    created_at = Field(...,description="创建时间")
    action_type = Field(...,description="系统消息类型")
    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime, _info):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    
    class Config:
        from_attributes = True