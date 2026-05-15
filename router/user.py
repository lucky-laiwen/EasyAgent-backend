from fastapi import APIRouter, Depends, HTTPException, status , Request,UploadFile, File
from crud import user as crud_user
from schemas.user import UserUpdate, UserCreate, UserOut ,UserLogin
from schemas.response import ResponseSchema
from sqlalchemy.orm import Session
from database import get_db
from utils.utils import create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from minio import Minio
import io
router = APIRouter(
    tags=['user'],
    prefix='/user',
)

client = Minio(
    endpoint='127.0.0.1:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)

bucket_name = "easy-agent"

# 上传文件
@router.post("/upload_file", response_model=ResponseSchema)
async def upload_file(
    file: UploadFile = File(...),
    _: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        file_bytes = await file.read()

        # 上传文件到 MinIO
        client.put_object(
            bucket_name=bucket_name,
            object_name=file.filename,
            data=io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=file.content_type
        )

        # 生成可访问的文件 URL（带签名）
        file_url = client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=file.filename,
        )

        return ResponseSchema.ok(
            message="upload_success",
            data={"url": file_url}
        )

    except Exception as e:
        return ResponseSchema.fail(message=str(e))


# 获取用户
@router.get("/get_user/{user_id}", response_model=ResponseSchema)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db),_: str = Depends(get_current_user)):
    user = crud_user.get_user(db=db, user_id=user_id)
    if not user:
        return ResponseSchema.fail(message="user_not_found")
    user_out = UserOut.model_validate(user)
    return ResponseSchema.ok(message="get_user_success",data=user_out)

# 获取所有用户
@router.get("/query_All", response_model=list[UserOut])
async def get_all_users(db: Session = Depends(get_db),_: str = Depends(get_current_user)):
    return crud_user.get_all_users(db)

# 注册
@router.post("/create_user", response_model=ResponseSchema)
async def create_user(user: UserCreate,request:Request, db: Session = Depends(get_db)):
    _ = request.state._
    payload = crud_user.create_user(db=db, name=user.name, email=user.email, password=user.password)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST , detail=_("user_registered")) 
    user_out = UserOut.model_validate(payload) 
    token = create_access_token(
        data={"id": str(user_out.id)},
        expires_delta=None
    )
    return ResponseSchema.ok(message=_("create_success"),data={
        "user": user_out,
        "access_token": token,
    })

# Swagger UI 登录
@router.post("/token")
async def get_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_obj, status_res = crud_user.login(db=db, email=form_data.username, password=form_data.password)
    
    if status_res == "not_found":
        raise HTTPException(status_code=404, detail="User not found")
    elif status_res == "wrong_password":
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_access_token(
        data={"id": str(user_obj.id)},
        expires_delta=None
    )
    return {"access_token": token, "token_type": "bearer"}

# 登录
@router.post("/login",response_model=ResponseSchema)
async def login_route(request:Request, form_data: UserLogin, db: Session = Depends(get_db)):
    """
    {
        "email": "mm@123.com",
        "password": "123456"
    }
    """
    user_obj, status_res = crud_user.login(db=db, email=form_data.email, password=form_data.password)
    _ = request.state._
    if status_res == "not_found":
        return ResponseSchema.fail(message=_("user_not_found")) 
    elif status_res == "wrong_password":
        return ResponseSchema.fail(message=_("invalid_password"))
    elif status_res == "frozen":
        return ResponseSchema.fail(message=_("user_frozen"))
    elif status_res == "banned":
        return ResponseSchema.fail(message=_("user_Banned"))

    token = create_access_token(
        data={"id": str(user_obj.id)},
        expires_delta=None
    )
    user_out = UserOut.model_validate(user_obj) 
    return ResponseSchema.ok(message=_("login_success"),data={
        "access_token": token,
        "token_type": "bearer",
        "user": user_out
    })

# 获取当前用户
@router.get("/current_user",response_model=UserOut)
async def current_user(request:Request, db: Session = Depends(get_db), token: str = Depends(get_current_user)):
    user_obj = crud_user.get_user(db=db, user_id=int(token))
    _ = request.state._
    if not user_obj:
        raise HTTPException(status_code=404, detail=_("user_not_found"))
    user_out = UserOut.model_validate(user_obj) 
    return user_out


# 注销
@router.delete("/logout",response_model=ResponseSchema)
async def logout_route(request:Request, db: Session = Depends(get_db), token: str = Depends(get_current_user)):
    _ = request.state._
    if not crud_user.delete_user(db=db, user_id=token):
        raise HTTPException(status_code=404, detail=_("user_not_found"))
    return ResponseSchema.ok(message=_("logout_success"))

# 更新用户
@router.put("/update_user",response_model=ResponseSchema)
async def update_route(user: UserUpdate, request:Request, db: Session = Depends(get_db), user_data: str = Depends(get_current_user)):
    _ = request.state._
    user_obj = crud_user.update_user(db=db, user_id=user_data, name=user.name, email=user.email,avatar=user.avatar)
    if not user_obj:
        raise HTTPException(status_code=401, detail=_("user_not_found"))
    user_out = UserOut.model_validate(user_obj) 
    return ResponseSchema.ok(message=_("update_success"),data=user_out)

# 忘记密码
@router.post("/forget_password",response_model=ResponseSchema,description="忘记密码")
async def forget_password_route(request:Request, user:UserLogin, db: Session = Depends(get_db)):
    _ = request.state._
    user_obj = crud_user.reset_password(db=db, email=user.email,password=user.password)
    if not user_obj:
        raise HTTPException(status_code=404, detail=_("user_not_found"))
    return ResponseSchema.ok(message=_("forgot_password_success"))