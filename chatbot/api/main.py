"""
chatbot/api/main.py
FastAPI entry point — single POST /chat/message endpoint.

Usage:
    uvicorn chatbot.api.main:app --reload
"""
import uuid
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chatbot.graph.builder import app as graph_app

# ── FastAPI app ──────────────────────────────────────────────────
api = FastAPI(title="Health Companion Chatbot", version="0.1.0")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Response schema ──────────────────────────────────────────────
class ChatResponse(BaseModel):
    session_id: str
    reply: str
    agent_type: str  # "companion" | "expert" | "crisis"
    transcribed_text: Optional[str] = None  # voice input transcription


def _intent_to_agent_type(intent: str) -> str:
    if intent == "medical":
        return "expert"
    if intent == "crisis":
        return "crisis"
    return "companion"


async def _save_upload(upload: UploadFile, suffix: str) -> str:
    """Save an uploaded file to a temp path and return the path string."""
    content = await upload.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(content)
    tmp.close()
    return tmp.name


@api.post("/chat/message", response_model=ChatResponse)
async def chat_message(
    user_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    # ── Normalise empty uploads (Swagger sends "string" placeholder) ─
    if image and not image.filename:
        image = None
    if audio and not audio.filename:
        audio = None

    # ── Session: auto-create if first message ────────────────
    if not session_id:
        session_id = uuid.uuid4().hex

    # ── Determine input mode ─────────────────────────────────
    input_mode = "voice" if audio else "text"

    # ── Build initial state ──────────────────────────────────
    # Note: history is managed by LangGraph's checkpointer (keyed on
    # thread_id = session_id), not via this field. We pass [] here;
    # the graph reads persisted history from the checkpointer automatically.
    state = {
        "user_input": text or "",
        "input_mode": input_mode,
        "chat_mode": "personal",
        "user_id": user_id,
        "history": [],
        "user_profile": {},
    }

    # ── Handle audio upload ──────────────────────────────────
    # Browser MediaRecorder sends WebM; save with original extension
    # so downstream ASR can detect format from content, not filename.
    if audio:
        ext = Path(audio.filename).suffix if audio.filename else ".webm"
        audio_path = await _save_upload(audio, suffix=ext)
        state["audio_path"] = audio_path

    # ── Handle image upload ──────────────────────────────────
    if image:
        image_path = await _save_upload(image, suffix=".jpg")
        state["image_paths"] = [image_path]

    # ── Invoke LangGraph ─────────────────────────────────────
    config = {"configurable": {"thread_id": session_id}}
    result = graph_app.invoke(state, config=config)

    # ── Extract response ─────────────────────────────────────
    reply = result.get("response", "")
    intent = result.get("intent", "chitchat")
    agent_type = _intent_to_agent_type(intent)

    transcribed = result.get("transcribed_text") if input_mode == "voice" else None

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        agent_type=agent_type,
        transcribed_text=transcribed,
    )
