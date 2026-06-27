import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from src.agent.graph import agent
from src.chat.utils import ChatHistoryHelper
from src.chat.session_state import SessionStateHelper
from src.chat.schemas import ChatReplyData
from src.chat.response_builder import build_chat_reply
from src.settings import settings


class ChatService:
    @staticmethod
    async def process_message(
        db: AsyncSession,
        session_id: str,
        user_message: str,
        timezone: str = "UTC",
        channel: str = "api",
    ) -> ChatReplyData:
        conversation_history = await ChatHistoryHelper.get_formatted_history(db, session_id)
        triage_state = await SessionStateHelper.get_session_state(db, session_id)
        pending_task = (triage_state.get("pending_confirmation") or {}) if triage_state else {}
        initial_state = {
            "user_query": user_message,
            "timezone": timezone,
            "session_id": session_id,
            "conversation_history": conversation_history,
            "intent": "",
            "extracted_fields": {},
            "pms_token": "",
            "pms_response": {},
            "final_response": "",
            "triage_state": triage_state,
            "pending_task_payload": pending_task or {},
        }
        result = await agent.ainvoke(initial_state)
        chat_reply = build_chat_reply(result)

        if result.get("clear_session_state"):
            await SessionStateHelper.clear_session_state(db, session_id)
        else:
            outgoing_state = result.get("triage_state")
            if not isinstance(outgoing_state, dict):
                outgoing_state = dict(triage_state or {})
            else:
                outgoing_state = dict(outgoing_state)
            if result.get("clear_pending_task"):
                outgoing_state["pending_confirmation"] = None
            new_pending = result.get("pending_task_payload")
            if (
                isinstance(new_pending, dict)
                and new_pending.get("task_payload")
                and outgoing_state.get("pending_confirmation") is not None
            ):
                outgoing_state["pending_confirmation"] = new_pending
            await SessionStateHelper.set_session_state(db, session_id, outgoing_state)

        await ChatHistoryHelper.append_turn(db, session_id, "user", user_message, channel)
        await ChatHistoryHelper.append_turn(
            db, session_id, "assistant", chat_reply.reply, channel
        )

        return chat_reply

    @staticmethod
    def plain_text(chat_reply: ChatReplyData) -> str:
        return chat_reply.reply


class WhatsappService:

    @staticmethod
    async def send_whatsapp_message(to, text):
        url = f"https://graph.facebook.com/v18.0/{settings.PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=headers)
            print(res.text)
