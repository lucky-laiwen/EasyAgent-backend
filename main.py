from fastapi import FastAPI, Depends
from router import user

app = FastAPI()

app.include_router(user.router)
