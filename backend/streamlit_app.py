"""
Covis AI — desktop chat UI. Requires the FastAPI server running (see main.py).

Run:
  uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

from datetime import datetime
import os
import uuid
from typing import Any

import requests
import streamlit as st

DEFAULT_API_BASE = os.environ.get("COVIS_API_BASE_URL", "http://127.0.0.1:8569")
CHAT_PATH = "/api/v1/chat"
REQUEST_TIMEOUT_S = 1000


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400..800;1,400..800&display=swap');

            html, body, [class*="css"] {
                font-family: "Plus Jakarta Sans", system-ui, -apple-system, sans-serif;
            }

            .block-container {
                padding-top: 1rem;
                padding-bottom: 5.5rem;
                max-width: 880px;
            }

            [data-testid="stHeader"] {
                background: transparent;
            }

            [data-testid="stToolbar"] {
                visibility: hidden;
                height: 0;
            }

            .stApp {
                background: radial-gradient(1200px 600px at 50% -10%, rgba(14, 165, 233, 0.09), transparent 55%),
                    linear-gradient(180deg, #f8fafc 0%, #eef2f7 50%, #f1f5f9 100%);
            }

            .covis-hero {
                padding: 0.25rem 0 1.25rem 0;
                margin-bottom: 1.25rem;
                border-bottom: 1px solid rgba(15, 23, 42, 0.07);
            }
            .covis-hero-top {
                display: flex;
                align-items: center;
                gap: 0.65rem;
                margin-bottom: 0.6rem;
            }
            .covis-logo-mark {
                width: 2.25rem;
                height: 2.25rem;
                border-radius: 10px;
                background: linear-gradient(145deg, #0ea5e9 0%, #0369a1 100%);
                box-shadow: 0 4px 14px rgba(14, 165, 233, 0.35);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .covis-logo-mark span {
                color: #fff;
                font-size: 1.1rem;
                font-weight: 800;
                letter-spacing: -0.06em;
            }
            .covis-hero h1 {
                font-size: 1.75rem;
                font-weight: 700;
                letter-spacing: -0.03em;
                color: #0f172a;
                margin: 0;
                line-height: 1.15;
            }
            .covis-hero p {
                margin: 0.35rem 0 0 0;
                font-size: 0.98rem;
                color: #475569;
                line-height: 1.55;
                max-width: 42rem;
            }
            .covis-badge {
                display: inline-block;
                margin-top: 0.65rem;
                font-size: 0.72rem;
                font-weight: 600;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: #0369a1;
                background: rgba(14, 165, 233, 0.12);
                border: 1px solid rgba(14, 165, 233, 0.22);
                padding: 0.2rem 0.55rem;
                border-radius: 999px;
            }

            .covis-suggestions-title {
                font-size: 0.82rem;
                font-weight: 600;
                color: #334155;
                margin: 0 0 0.75rem 0;
                letter-spacing: 0.01em;
            }

            /* Starter chips: main column only */
            section.main div[data-testid="stHorizontalBlock"] button {
                width: 100%;
                min-height: 3.1rem;
                border-radius: 12px !important;
                font-weight: 500 !important;
                font-size: 0.88rem !important;
                line-height: 1.35 !important;
                white-space: normal !important;
                height: auto !important;
                padding: 0.65rem 0.85rem !important;
                background: #ffffff !important;
                color: #1e293b !important;
                border: 1px solid rgba(15, 23, 42, 0.1) !important;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05), 0 2px 8px rgba(15, 23, 42, 0.04) !important;
                transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease !important;
            }
            section.main div[data-testid="stHorizontalBlock"] button:hover {
                border-color: rgba(14, 165, 233, 0.55) !important;
                box-shadow: 0 2px 12px rgba(14, 165, 233, 0.12) !important;
                transform: translateY(-1px);
            }
            section.main div[data-testid="stHorizontalBlock"] button:active {
                transform: translateY(0);
            }
            section.main div[data-testid="stHorizontalBlock"] button p {
                font-size: 0.88rem !important;
            }

            [data-testid="stChatMessage"] {
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid rgba(15, 23, 42, 0.07);
                border-radius: 16px;
                margin-bottom: 0.75rem;
                box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
            }

            [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                border-color: rgba(14, 165, 233, 0.18);
            }

            [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
                background: #ffffff;
                border-color: rgba(15, 23, 42, 0.08);
            }

            /* Pinned chat composer — soften hard black dock */
            [data-testid="stBottomBlockContainer"] {
                background: linear-gradient(180deg,
                    rgba(241, 245, 249, 0) 0%,
                    rgba(241, 245, 249, 0.92) 18%,
                    #f1f5f9 100%) !important;
                border-top: 1px solid rgba(15, 23, 42, 0.08) !important;
                padding-top: 0.5rem !important;
                padding-bottom: 0.65rem !important;
                backdrop-filter: blur(10px);
            }

            [data-testid="stChatInput"] {
                background: transparent !important;
                border: none !important;
                padding: 0 0.5rem !important;
            }

            [data-testid="stChatInput"] > div {
                background: #ffffff !important;
                border: 1px solid rgba(15, 23, 42, 0.1) !important;
                border-radius: 14px !important;
                box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06) !important;
            }

            [data-testid="stChatInput"] textarea {
                color: #0f172a !important;
                background: transparent !important;
                caret-color: #0284c7 !important;
            }

            [data-testid="stChatInput"] textarea::placeholder {
                color: #94a3b8 !important;
            }

            [data-testid="stChatInput"] button {
                background: linear-gradient(145deg, #0ea5e9, #0284c7) !important;
                border: none !important;
                color: #fff !important;
                border-radius: 10px !important;
                box-shadow: 0 2px 8px rgba(2, 132, 199, 0.35) !important;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(195deg, #0f172a 0%, #1e293b 55%, #0f172a 100%);
                border-right: 1px solid rgba(148, 163, 184, 0.12);
            }
            [data-testid="stSidebar"] .stMarkdown,
            [data-testid="stSidebar"] label {
                color: #e2e8f0 !important;
            }
            [data-testid="stSidebar"] hr {
                border-color: rgba(148, 163, 184, 0.22);
            }
            [data-testid="stSidebar"] .stButton button {
                width: 100%;
                border-radius: 10px;
                font-weight: 600;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _call_chat_api(
    base_url: str,
    message: str,
    session_id: str,
    timezone: str,
) -> tuple[bool, dict[str, Any] | str]:
    url = base_url.rstrip("/") + CHAT_PATH
    try:
        r = requests.post(
            url,
            json={
                "message": message,
                "timezone": timezone,
                "session_id": session_id,
            },
            timeout=REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as e:
        return False, f"Could not reach the API ({url}). Is the server running? Details: {e}"

    try:
        payload: dict[str, Any] = r.json()
    except ValueError:
        return False, f"Invalid JSON from server (HTTP {r.status_code})."

    if r.status_code >= 400:
        msg = payload.get("message") if isinstance(payload, dict) else str(payload)
        return False, msg or f"Request failed (HTTP {r.status_code})."

    if isinstance(payload, dict) and payload.get("succeeded") is False:
        return False, str(payload.get("message", "Request failed."))

    if isinstance(payload, dict) and "data" in payload:
        data = payload["data"]
        if isinstance(data, str):
            return True, {
                "reply": data,
                "actions": [],
                "tasks": [],
                "response_kind": "text",
            }
        if isinstance(data, dict):
            return True, {
                "reply": str(data.get("reply", "")),
                "actions": data.get("actions") or [],
                "tasks": data.get("tasks") or [],
                "response_kind": data.get("response_kind", "text"),
            }
        return True, str(data)

    return False, "Unexpected response shape from API."


def _render_assistant_actions(msg_index: int, actions: list[dict[str, Any]]) -> None:
    clickable = [
        a
        for a in actions
        if a.get("type") in ("quick_reply", "prefill")
        and (a.get("payload") or "").strip()
    ]
    if not clickable:
        return
    cols = st.columns(min(len(clickable), 3), gap="small")
    for col, action in zip(cols, clickable, strict=False):
        label = str(action.get("label", "Option"))
        action_id = str(action.get("id", label))
        if col.button(label, key=f"action_{msg_index}_{action_id}", use_container_width=True):
            st.session_state["_pending"] = str(action.get("payload", ""))
            st.rerun()


def _init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())


def _build_chat_export_markdown(messages: list[dict[str, str]], session_id: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Covis AI Chat Export",
        "",
        f"- Session ID: `{session_id}`",
        f"- Exported At: `{timestamp}`",
        "",
        "---",
        "",
    ]

    for idx, message in enumerate(messages, start=1):
        role = str(message.get("role", "assistant")).title()
        content = str(message.get("content", "")).strip() or "_(empty message)_"
        lines.append(f"### {idx}. {role}")
        lines.append(content)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    st.set_page_config(
        page_title="Covis AI",
        page_icon="◆",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    _inject_styles()
    _init_session_state()

    with st.sidebar:
        st.markdown("### Session")
        st.caption("Each session keeps its own history on the server.")
        if st.button("New conversation", type="primary"):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

        st.markdown("---")
        st.markdown("### Connection")
        api_base = st.text_input(
            "API base URL",
            value=st.session_state.get("api_base", DEFAULT_API_BASE),
            help="FastAPI root, e.g. http://127.0.0.1:8000",
        )
        st.session_state.api_base = api_base

        tz = st.text_input("Timezone", value=st.session_state.get("tz", "UTC"))
        st.session_state.tz = tz

        st.markdown("---")
        st.caption(
            f"Session ID\n`{st.session_state.session_id[:8]}…`"
        )
        st.download_button(
            "Export chat (.md)",
            data=_build_chat_export_markdown(
                st.session_state.messages,
                st.session_state.session_id,
            ),
            file_name=f"covis-chat-{st.session_state.session_id[:8]}.md",
            mime="text/markdown",
            use_container_width=True,
            disabled=not st.session_state.messages,
            help="Download the current conversation transcript.",
        )

    st.markdown(
        """
        <div class="covis-hero">
            <div class="covis-hero-top">
                <div class="covis-logo-mark" aria-hidden="true"><span>C</span></div>
                <h1>Covis AI</h1>
            </div>
            <p>Chat like your project lead on WhatsApp — board updates, logging work, and straight talk in plain language.</p>
            <span class="covis-badge">Task agent</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pending = st.session_state.pop("_pending", None)
    prompt = st.chat_input("Message Covis AI…")
    user_text = (pending or prompt or "").strip() or None

    if not st.session_state.messages and not user_text:
        st.markdown(
            '<p class="covis-suggestions-title">Suggested starters</p>',
            unsafe_allow_html=True,
        )
        cols = st.columns(3, gap="small")
        starters = [
            "What can you help me with?",
            "List my open tasks",
            "Create a task: review API docs by Friday",
        ]
        for col, text in zip(cols, starters, strict=True):
            if col.button(
                text,
                key=f"starter_{text}",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state["_pending"] = text
                st.rerun()

    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                tasks = msg.get("tasks") or []
                if tasks:
                    with st.expander("Task details", expanded=False):
                        st.dataframe(tasks, use_container_width=True, hide_index=True)
                _render_assistant_actions(idx, msg.get("actions") or [])

    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        api_base = st.session_state.get("api_base", DEFAULT_API_BASE)
        tz = st.session_state.get("tz", "UTC")

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                ok, reply_data = _call_chat_api(
                    api_base,
                    user_text,
                    st.session_state.session_id,
                    tz,
                )
            if not ok:
                st.error(str(reply_data))
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"**Error:** {reply_data}"}
                )
            elif isinstance(reply_data, dict):
                st.markdown(reply_data["reply"])
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": reply_data["reply"],
                        "actions": reply_data.get("actions") or [],
                        "tasks": reply_data.get("tasks") or [],
                    }
                )
            else:
                st.markdown(str(reply_data))
                st.session_state.messages.append(
                    {"role": "assistant", "content": str(reply_data)}
                )

        st.rerun()


if __name__ == "__main__":
    main()
