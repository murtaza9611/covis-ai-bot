from fastapi import APIRouter
from src.chat.router import router as chat_router

api_router = APIRouter()
api_router.include_router(chat_router, prefix="/v1", tags=["Chat"])
