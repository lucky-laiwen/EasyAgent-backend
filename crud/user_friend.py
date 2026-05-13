from sqlalchemy.orm import Session
from models.user_friend import UserFriend
from models.user import User   
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

# 查询待确认的好友
def get_pending_friend_requests(db: Session, user_id: int, friend_id: int):
    friend = db.query(UserFriend).filter(
        and_(
            UserFriend.status == 0,
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
    db_user_friend = UserFriend(user_id=user_id, friend_id=friend_id,status=0)
    friend_info = db.query(User).filter(User.id == friend_id).first()    
    db.add(db_user_friend)
    db.commit()
    db.refresh(db_user_friend)
    return friend_info

# 查询好友列表
def get_user_friends_list(db: Session, user_id: int):
    friends = db.query(UserFriend).filter(or_(
        UserFriend.user_id == user_id,
        UserFriend.friend_id == user_id
    ), UserFriend.status == 1).all()
    return friends

# 查询好友（模糊查询）
def search_and_classify_friends(db: Session, current_user_id: int, name_or_email: str):
    """
    搜索好友并按互为好友关系分类
    """
    # 先获取所有用户信息
    friends_with_user_info = db.query(User).filter(
        or_(
            User.name.like(f"%{name_or_email}%"),
            User.email.like(f"%{name_or_email}%")
        )
    ).all()
    
    mutual_friends = []      # 已互为好友
    non_mutual_friends = []  # 未互为好友
    pending_mutual_friends = []  # 待确认
    # 对每个用户检查是否互为好友
    for user in friends_with_user_info:
        # 确保不是当前用户自己
        if user.id != current_user_id:
            if get_user_friend(db, current_user_id, user.id):
                mutual_friends.append(user)
            elif get_pending_friend_requests(db, current_user_id, user.id):
                pending_mutual_friends.append(user)
            else:
                non_mutual_friends.append(user)
    
    return {
        'pending_mutual_friends': pending_mutual_friends,   # 待确认
        'mutual_friends': mutual_friends,      # 互为好友的用户列表
        'non_mutual_friends': non_mutual_friends  # 不是互为好友的用户列表
    }

# 确认好友
def confirm_friend_utils(db: Session, user_id: int, friend_id: int , action_type: int):
    friend = db.query(UserFriend).filter(
        and_(
            UserFriend.user_id == user_id,
            UserFriend.friend_id == friend_id,
            UserFriend.status == 0
        )
    ).first()

    if friend:
        friend.status = action_type
        db.commit()
        db.refresh(friend)
        return friend
    else:
        return None
