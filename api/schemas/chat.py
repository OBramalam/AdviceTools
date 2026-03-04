from pydantic import BaseModel
from typing import List, Optional, Dict, Literal


class ChatMessageRequest(BaseModel):
    message: str
    context: Literal["plan_builder", "dashboard"] = "plan_builder"
    plan_id: Optional[int] = None


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]


class ExportChatRequest(BaseModel):
    """Request to export chat and optionally trigger parsing/simulation."""
    trigger_parser: bool = False  # If True, also run parser and create financial plan
    context: Literal["plan_builder", "dashboard"] = "plan_builder"
    plan_id: Optional[int] = None


class ExportChatResponse(BaseModel):
    success: bool
    chat_text: Optional[str] = None
    filepath: Optional[str] = None
    error: Optional[str] = None

