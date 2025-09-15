from fastapi import APIRouter,Depends
from utils.utils import get_current_user
from schemas.chat import CreateChat , ChatItem
from crud.chat import create_chat,get_chat_by_user_id
from schemas.response import ResponseSchema
from database import get_db
from sqlalchemy.orm import Session
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)
# 创建聊天
@router.post('/create_chat',response_model=ResponseSchema)
async def create_chat_router( chatData: CreateChat, db:Session = Depends(get_db) , user: str = Depends(get_current_user)):
    chat_obj = create_chat(db,user,chatData.message,chatData.title)
    if not chat_obj:
        return ResponseSchema.fail(message="创建聊天失败",data=None)
    chat_out = CreateChat.model_validate(chat_obj)
    return ResponseSchema.ok(message="创建聊天成功",data=chat_out)

# 查询对应用户的所有聊天
@router.get('/get_chat_list',response_model=ResponseSchema)
async def get_chat_list_router(db:Session = Depends(get_db), user: str = Depends(get_current_user),page_size:int=3,last_id:int|None=None):
    user_id = user
    chat_list =get_chat_by_user_id(db,user_id,page_size,last_id)
    if not chat_list:
        return ResponseSchema.fail(message="查询聊天列表失败",data=None)
    chat_list_out = [ChatItem.model_validate(chat) for chat in chat_list["data"]]
    return ResponseSchema.ok(message="查询聊天列表成功",data={"chat_list":chat_list_out,"next_last_id":chat_list["next_last_id"]})