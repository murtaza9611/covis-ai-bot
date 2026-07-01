from fastapi import APIRouter
from src.chat.router import router as chat_router
from src.qa.router import router as qa_router

api_router = APIRouter()
api_router.include_router(chat_router, prefix="/v1", tags=["Chat"])
api_router.include_router(qa_router, prefix="/v1/qa", tags=["QA"])
