from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src import api_router
from src.settings import settings
from contextlib import asynccontextmanager
import uvicorn
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session, initialize_database
from src.chat.services import (
    WhatsappService,
    ChatService,
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - handles startup and shutdown"""
    
    # ==================== STARTUP ====================
    try:
        
        print("=" * 60)
        print("🚀 APPLICATION STARTUP")
        print("=" * 60)
        
        # Initialize database
        print("📊 Initializing database...")
        await initialize_database()
        print("✅ Database initialized")

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        traceback.print_exc()
        raise
    yield
    print("Application shutdown complete")

app = FastAPI(
    lifespan=lifespan,
    title="Covis Task Agent",
    description="Agentic AI assistant for project task management",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


# @app.get("/webhook", tags=["WhatsApp"])
# async def verify(request: Request):
#     if request.query_params.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN:
#         return int(request.query_params.get("hub.challenge", "0"))
#     return {"error": "verification failed"}


@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params

    if params.get("hub.mode") == "subscribe" and \
       params.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN:
        
        return int(params.get("hub.challenge"))

    return {"error": "verification failed"}


@app.post("/webhook")
async def webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    data = await request.json()

    try:
        value = data["entry"][0]["changes"][0]["value"]
        messages = value.get("messages", [])
        if not messages:
            return {"status": "ok"}

        message = messages[0]
        user_text = message.get("text", {}).get("body", "").strip()
        sender = message.get("from", "")
        if not user_text or not sender:
            return {"status": "ok"}

        chat_reply = await ChatService.process_message(
            db=db,
            session_id=sender,
            user_message=user_text,
            timezone="UTC",
            channel="meta-whatsapp",
        )

        await WhatsappService.send_whatsapp_message(sender, ChatService.plain_text(chat_reply))

    except Exception as e:
        print("Error:", e)

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.SERVER_HOST, port=settings.SERVER_PORT)
