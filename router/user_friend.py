from fastapi import APIRouter,Depends
from schemas.response import ResponseSchema
from crud.user_friend import get_user_friend , create_user_friend,get_user_friends_list,search_and_classify_friends
from database import get_db
from sqlalchemy.orm import Session
from utils.utils import get_current_user
from  schemas.user_friend import UserFriend,UserFriendOut,AddFriendSchema
from schemas.user import UserOut
router = APIRouter(
    tags=["user_friend"],
    prefix="/user_friend"
)

@router.post("/add_friend", response_model=ResponseSchema)
async def add_friend(
    data: AddFriendSchema,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    friend_id = data.friend_id

    if int(user_id) == friend_id:
        return ResponseSchema.fail(message="不能添加自己为好友")

    is_friend = get_user_friend(db, user_id, friend_id)
    if is_friend:
        return ResponseSchema.fail(message="好友已存在")

    db_user_friend = create_user_friend(db, user_id, friend_id)
    user_friend = UserOut.model_validate(db_user_friend)

    return ResponseSchema.ok(message="好友添加成功", data=user_friend)


# 查询好友列表
@router.get("/get_friend_list", response_model=ResponseSchema)
async def get_user_friend_list(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    friends = get_user_friends_list(db, user_id)

    if not friends:
        return ResponseSchema.ok(message="好友列表为空", data=[])

    data = []
    for f in friends:
        # 确定对方是谁
        friend_user = f.friend if f.user_id == int(user_id) else f.user
        # Pydantic 嵌套
        data.append(
            UserFriendOut.model_validate({
                "id": f.id,
                "status": f.status,
                "created_at": f.created_at,
                "friend": friend_user
            })
        )

    return ResponseSchema.ok(message="获取成功", data=data)

# 搜索好友
@router.get("/search_friend", response_model=ResponseSchema)
async def search_friend(friend_name: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    friends = search_and_classify_friends(db, user_id,friend_name)
    if not friends:
        return ResponseSchema.fail(message="没有找到该用户", data=[])
    mutual_friends_outs = [
        UserOut.model_validate(friend)
        for friend in friends["mutual_friends"]
    ]
    non_mutual_friends_outs = [
        UserOut.model_validate(friend)
        for friend in friends["non_mutual_friends"]
    ]
    pending_mutual_friends_outs = [
        UserOut.model_validate(friend)
        for friend in friends["pending_mutual_friends"]
    ]
    return ResponseSchema.ok(message="获取成功", data={
        "pending_mutual_friends": pending_mutual_friends_outs,
        "mutual_friends": mutual_friends_outs,
        "non_mutual_friends": non_mutual_friends_outs
    })
    