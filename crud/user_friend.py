from sqlalchemy.orm import Session
from models.user_friend import UserFriend   
from sqlalchemy import or_, and_
# 查询是否互为好友
def get_user_friend(db: Session, user_id: int, friend_id: int):
    friend = db.query(UserFriend).filter(
        and_(
            UserFriend.status == 1,
            or_(
                and_(
                    UserFriend.user_id == user_id,
                    UserFriend.friend_id == friend_id
                ),
                and_(
                    UserFriend.user_id == friend_id,
                    UserFriend.friend_id == user_id
                )
            )
        )
    ).first()

    return friend is not None


def create_user_friend(db: Session, user_id: int, friend_id: int):
    db_user_friend = UserFriend(user_id=user_id, friend_id=friend_id,status=1)    
    db.add(db_user_friend)
    db.commit()
    db.refresh(db_user_friend)
    return db_user_friend

# 查询好友列表
def get_user_friends_list(db: Session, user_id: int):
    friends = db.query(UserFriend).filter(or_(
        UserFriend.user_id == user_id,
        UserFriend.friend_id == user_id
    ), UserFriend.status == 1).all()
    return friends
