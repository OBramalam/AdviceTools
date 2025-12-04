import os
import sys
from datetime import datetime
from typing import Generator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.chat_service import ChatService
from api.dependencies import get_db, get_current_active_user
from api.schemas.chat import (
    ChatMessageRequest,
    ChatHistoryResponse,
    ChatMessage,
    ExportChatRequest,
    ExportChatResponse,
)
from infra.database.models.user import User

router = APIRouter()

# Initialize chat service (singleton pattern)
_chat_service: ChatService = None


def get_chat_service() -> ChatService:
    """Get or create the chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


@router.post("/message")
async def send_chat_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a chat message and stream the assistant's response.
    
    Returns a Server-Sent Events (SSE) stream of the response chunks.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )
    
    chat_service = get_chat_service()
    
    def generate_stream() -> Generator[str, None, None]:
        """Generator function that yields SSE-formatted chunks."""
        try:
            for chunk in chat_service.send_message(current_user.id, request.message):
                # Format as Server-Sent Events
                yield f"data: {chunk}\n\n"
            # Send completion signal
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Send error in SSE format
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering for nginx
        }
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    current_user: User = Depends(get_current_active_user)
):
    """Get the chat history for the current user."""
    chat_service = get_chat_service()
    history = chat_service.get_chat_history(current_user.id)
    
    messages = [
        ChatMessage(role=msg["role"], content=msg["content"])
        for msg in history
    ]
    
    return ChatHistoryResponse(messages=messages)


@router.delete("/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_active_user)
):
    """Clear the chat history for the current user."""
    chat_service = get_chat_service()
    chat_service.clear_chat_history(current_user.id)
    return {"success": True, "message": "Chat history cleared"}


@router.post("/export", response_model=ExportChatResponse)
async def export_chat(
    request: ExportChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export chat history as a text file.
    
    Optionally trigger the parser to extract data and create a financial plan.
    """
    chat_service = get_chat_service()
    
    try:
        # Export chat history as text
        chat_text = chat_service.export_chat_history(current_user.id)
        
        if not chat_text:
            return ExportChatResponse(
                success=False,
                error="No chat history to export"
            )
        
        # Save to file
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        
        filename = f"conversation_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = uploads_dir / filename
        
        filepath.write_text(chat_text, encoding="utf-8")
        
        # If requested, trigger parser
        if request.trigger_parser:
            try:
                from services.parser_service import ParserService
                
                parser = ParserService(
                    user_id=current_user.id,
                    filepath=str(filepath),
                    db=db
                )
                financial_plan, cash_flows = parser.extract_data()
                
                return ExportChatResponse(
                    success=True,
                    chat_text=chat_text,
                    filepath=str(filepath)
                )
            except Exception as parse_error:
                return ExportChatResponse(
                    success=True,  # Export succeeded
                    chat_text=chat_text,
                    filepath=str(filepath),
                    error=f"Export succeeded but parsing failed: {str(parse_error)}"
                )
        
        return ExportChatResponse(
            success=True,
            chat_text=chat_text,
            filepath=str(filepath)
        )
        
    except Exception as e:
        return ExportChatResponse(
            success=False,
            error=str(e)
        )

