from sqlalchemy.orm import Session

from models.user import User
from typing import Optional, Literal
from utils.utils import get_password_hash , verify_password

# 查询用户
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


# 查询所有用户
def get_all_users(db: Session) -> list[User]:
    return db.query(User).all()


# 用户登录
def login(db: Session, email: str, password: str) -> tuple[
    Optional[User], Literal["not_found", "wrong_password", "ok"]]:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None, "not_found"

    if not verify_password(password, user.password):
        return None, "wrong_password"

    return user, "ok"


# 创建用户
def create_user(db: Session, name: str, email: str, password: str) -> User:
    # 1. 检查邮箱是否存在
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None  # 或者抛 FastAPI 的 HTTPException

    # 2. 创建用户
    hash_password = get_password_hash(password)
    user = User(name=name, email=email, password=hash_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# 注销用户
def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False  # 或者抛 FastAPI 的 HTTPException
    db.delete(user)
    db.commit()
    return True

# 更新用户信息
def update_user(db: Session, user_id: int, name: Optional[str], email: Optional[str], password: Optional[str]) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None  # 或者抛 FastAPI 的 HTTPException
    if name and email and password:
        user.name = name
        user.email = email
        hash_password = get_password_hash(password)
        user.password = hash_password
    db.commit()
    db.refresh(user)
    return user

# 重置密码
def reset_password(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None  # 或者抛 FastAPI 的 HTTPException
    hash_password = get_password_hash(password)
    user.password = hash_password
    db.commit()
    db.refresh(user)
    return user
