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
        raise ValueError("Email already registered")  # 或者抛 FastAPI 的 HTTPException

    # 2. 创建用户
    hash_password = get_password_hash(password)
    user = User(name=name, email=email, password=hash_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


