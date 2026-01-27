from sqlalchemy.orm import Session
from typing import Optional
from models.chat import Chat
from models.user import User
from sqlalchemy import literal
from models.chat_share import ChatShare

# 查询用户是否存在
def get_user_by_id(db:Session,user_id:int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    return True

# 创建聊天
def create_chat(db: Session, user_id: int, id: int,title:str) -> Optional[Chat]:
    if not get_user_by_id(db, user_id):
        return None
    is_have_chat = db.query(Chat).filter(Chat.id == id, Chat.user_id == user_id).first()
    if not is_have_chat:
        chat = Chat(user_id=user_id, title= title)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat
    else:
        return is_have_chat


# 获取对应用户的聊天记录（包括自己创建的和被分享的），并标注来源
def get_chat_by_user_id(
    db: Session,
    user_id: int,
    page_size: int,
    last_id: int | None = None
) -> Optional[dict]:

    if not get_user_by_id(db, user_id):
        return None

    # -------------------------
    # 1️⃣ 我自己的聊天
    # -------------------------
    own_query = (
        db.query(
            Chat,
            literal("own").label("source")
        )
        .filter(Chat.user_id == user_id)
    )

    if last_id:
        own_query = own_query.filter(Chat.id < last_id)

    # -------------------------
    # 2️⃣ 分享给我，且我有编辑权限的聊天
    # -------------------------
    shared_query = (
        db.query(
            Chat,
            literal("shared").label("source")
        )
        .join(ChatShare, ChatShare.chat_id == Chat.id)
        .filter(
            ChatShare.shared_to_id == user_id,
            ChatShare.permission == 2
        )
    )

    if last_id:
        shared_query = shared_query.filter(Chat.id < last_id)

    # -------------------------
    # 3️⃣ 合并 + 排序 + 分页
    # -------------------------
    union_query = (
        own_query
        .union_all(shared_query)
        .order_by(Chat.id.desc())
        .limit(page_size)
    )

    results = union_query.all()

    # -------------------------
    # 4️⃣ 处理返回结构
    # -------------------------
    chats = []
    for chat, source in results:
        setattr(chat, "source", source)
        chats.append(chat)

    next_last_id = chats[-1].id if chats else None

    return {
        "data": chats,
        "next_last_id": next_last_id
    }

# 更新聊天标题
def update_chat_title(db:Session,user_id:int,chat_id:int,title:str) -> Optional[Chat]:
    if not get_user_by_id(db,user_id):
        return None
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        return None
    chat.title = title
    db.commit()
    db.refresh(chat)
    return chat

# 删除聊天
def delete_chat(db: Session, user_id: int, chat_id: int):
    if not get_user_by_id(db, user_id):
        return None

    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        return None

    try:
        db.delete(chat)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting chat {chat_id}: {e}")
        return False
    
# 查询具体聊天内容
def get_chat_by_id(db: Session, chat_id: int) -> Optional[Chat]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return None
    return chat

