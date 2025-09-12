from fastapi import APIRouter,Depends
from utils.utils import get_current_user
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.get('/')
async def get_chat(_: str = Depends(get_current_user)):
    return {'message': 'Hello, World!'}