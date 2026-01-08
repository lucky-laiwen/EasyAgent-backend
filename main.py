from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import user, chat,user_chat,user_friend
from utils.i18n import i18n_middleware

app = FastAPI()

# 注册 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


app.middleware("http")(i18n_middleware)

app.include_router(user.router)
app.include_router(chat.router)
app.include_router(user_chat.router)
app.include_router(user_friend.router)
