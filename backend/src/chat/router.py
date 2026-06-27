from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat.schemas import ChatRequest, ChatResponse
from src.response import BuildJSONResponses
from src.database import get_async_session
from src.chat.services import ChatService
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, summary="Chat with the task management agent")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_async_session),
) -> ChatResponse:
    try:
        chat_reply = await ChatService.process_message(
            db=db,
            session_id=request.session_id,
            user_message=request.message,
            timezone=request.timezone,
            channel="api",
        )

        print(f"\n\nUser: {request.message}\n")
        print(f"Agent: {chat_reply.reply}\n\n")

        return BuildJSONResponses.success_response(
            data=chat_reply.model_dump(),
            message="Chat response generated successfully",
        )
    
    except Exception as e:
        return BuildJSONResponses.raise_exception(message=f"Error occurred while processing chat request: {str(e)}")
    

@router.post("/twilio-webhook", tags=["Twilio"])
async def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
) -> Response:
    session_id = From
    user_message = Body.strip()

    try:
        chat_reply = await ChatService.process_message(
            db=db,
            session_id=session_id,
            user_message=user_message,
            timezone="UTC",
            channel="twilio-whatsapp",
        )
        reply = ChatService.plain_text(chat_reply)

    except Exception:
        reply = "Sorry, I could not process your message right now. Please try again."

    twilio_response = MessagingResponse()
    twilio_response.message(reply)
    return Response(content=str(twilio_response), media_type="application/xml")
