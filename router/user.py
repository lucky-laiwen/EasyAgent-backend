from fastapi import APIRouter, Depends, HTTPException, status
from crud import user as crud_user
from schemas.user import User as UserSchema, UserCreate, UserLogin, LoginSchema, UserOut
from schemas.response import ResponseSchema
from sqlalchemy.orm import Session
from database import get_db
from utils.utils import create_access_token, bearer_token,decode_token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(
    tags=['user'],
    prefix='/user'
)


@router.get("/get_user/{user_id}", response_model=UserSchema)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    return crud_user.get_user(db=db, user_id=user_id)


@router.get("/query_All", response_model=list[UserSchema])
async def get_all_users(db: Session = Depends(get_db)):
    return crud_user.get_all_users(db)


@router.post("/create_user", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return crud_user.create_user(db=db, name=user.name, email=user.email, password=user.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 登录
@router.post("/login",response_model=ResponseSchema)
async def login_route(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_obj, status_res = crud_user.login(db=db, email=form_data.username, password=form_data.password)

    if status_res == "not_found":
        raise HTTPException(status_code=404, detail="User not found")
    elif status_res == "wrong_password":
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_access_token(
        data={"id": str(user_obj.id)},
        expires_delta=None
    )
    user_out = UserOut.model_validate(user_obj) 
    return ResponseSchema.ok(message="登陆成功",data={
        "access_token": token,
        "token_type": "bearer",
        "user": user_out
    })


@router.post("/get_current_user", response_model=ResponseSchema)
async def get_current_user(
    token: str = Depends(bearer_token),  # 从请求头拿 token
    db: Session = Depends(get_db)
):
    # 定义统一的异常
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # 查询数据库
    user_obj = crud_user.get_user(db=db, user_id=int(user_id))
    if not user_obj:
        raise credentials_exception

    # 转换成响应模型
    user_out = UserOut.model_validate(user_obj)
    return ResponseSchema.ok(message="Current user fetched", data=user_out)
