from fastapi import APIRouter,Depends
from schemas.response import ResponseSchema
from crud.system_message import get_system_messages_by_user_id,create_system_message,update_system_message_status
from database import get_db
from sqlalchemy.orm import Session
from utils.utils import get_current_user
from schemas.system_message import SystemMessage
router = APIRouter(
    prefix="/system_info",
    tags=["system_info"]
)

@router.get("/get_system_messages")
async def get_system_messages_router(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    system_messages = get_system_messages_by_user_id(db, user)
    return ResponseSchema.ok(message="获取系统消息成功", data=[SystemMessage.model_validate(m) for m in system_messages])

@router.post("/update_system_message_status")
async def update_system_message_status_router(message_id: int,title: str,content: str,action_type: int, db: Session = Depends(get_db)):
    system_message = update_system_message_status(db, message_id,title,content,action_type)
    if system_message:
        return ResponseSchema.ok(message="更新系统消息状态成功", data=SystemMessage.model_validate(system_message))
    else:
        return ResponseSchema.fail(message="更新系统消息状态失败")

@router.post("/create_system_message")
async def create_system_message_router(system_message: SystemMessage, db: Session = Depends(get_db)):
    system_message = create_system_message(db, system_message.title, system_message.content, system_message.user_id, action_type=0, source_id=system_message.source_id)   
    if system_message:
        return ResponseSchema.ok(message="创建系统消息成功", data=SystemMessage.model_validate(system_message))
    return ResponseSchema.fail(message="创建系统消息失败", data=None)