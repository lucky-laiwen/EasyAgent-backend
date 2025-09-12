from fastapi import FastAPI
from router import user , chat
from utils.i18n import i18n_middleware
app = FastAPI()
app.middleware("http")(i18n_middleware)
app.include_router(user.router)
app.include_router(chat.router)
