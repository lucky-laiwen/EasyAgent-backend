from fastapi import FastAPI, Depends
from router import user
from utils.i18n import i18n_middleware
app = FastAPI()
app.middleware("http")(i18n_middleware)
app.include_router(user.router)
