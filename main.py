from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router import user, chat, user_chat, user_friend , system_message
from utils.i18n import i18n_middleware
from database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ 应用启动时
    print("🚀 初始化数据库")
    init_db()

    yield

    # ✅ 应用关闭时（可选）
    print("🛑 应用关闭")


app = FastAPI(lifespan=lifespan)

# 注册 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 i18n 中间件
app.middleware("http")(i18n_middleware)

# 注册路由
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(user_chat.router)
app.include_router(user_friend.router)
app.include_router(system_message.router)
