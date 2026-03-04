import os
import sys
from datetime import datetime
from typing import Generator, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.chat_service import (
    ChatService,
    CHAT_CONTEXT_PLAN_BUILDER,
    CHAT_CONTEXT_DASHBOARD,
)
from api.dependencies import get_db, get_current_active_user
from api.schemas.chat import (
    ChatMessageRequest,
    ChatHistoryResponse,
    ChatMessage,
    ExportChatRequest,
    ExportChatResponse,
)
from infra.database.models.user import User
from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.cashflow import CashFlow as DBCashFlow
from infra.database.models.portfolio import Portfolio as DBPortfolio

router = APIRouter()

_chat_service: ChatService = None


def get_chat_service() -> ChatService:
    """Get or create the chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def build_plan_context(plan_id: int, user_id: int, db: Session) -> Optional[str]:
    """
    Build a text summary of the plan (plan details, cash flows, portfolios) for the dashboard AI.
    Returns None if the plan is not found or does not belong to the user.
    """
    plan = (
        db.query(DBFinancialPlan)
        .filter(
            DBFinancialPlan.id == plan_id,
            DBFinancialPlan.user_id == user_id,
        )
        .first()
    )
    if not plan:
        return None

    lines = [
        "### Plan",
        f"- Name: {plan.name}",
        f"- Description: {plan.description or '(none)'}",
        f"- Start age: {plan.start_age}, Retirement age: {plan.retirement_age}, Plan end age: {plan.plan_end_age}",
        f"- Portfolio target value: {plan.portfolio_target_value}",
        "",
    ]

    cashflows = db.query(DBCashFlow).filter(DBCashFlow.plan_id == plan_id).all()
    incomes = [c for c in cashflows if c.amount > 0]
    expenses = [c for c in cashflows if c.amount < 0]

    if incomes:
        lines.append("### Incomes")
        for c in incomes:
            start = c.start_date.isoformat() if c.start_date else "—"
            end = c.end_date.isoformat() if c.end_date else "—"
            lines.append(f"- {c.name}: {c.description or '(no description)'}; amount {c.amount}; {c.periodicity} (frequency {c.frequency}); {start} to {end}")
        lines.append("")

    if expenses:
        lines.append("### Expenses")
        for c in expenses:
            start = c.start_date.isoformat() if c.start_date else "—"
            end = c.end_date.isoformat() if c.end_date else "—"
            lines.append(f"- {c.name}: {c.description or '(no description)'}; amount {c.amount}; {c.periodicity} (frequency {c.frequency}); {start} to {end}")
        lines.append("")

    portfolios = db.query(DBPortfolio).filter(DBPortfolio.plan_id == plan_id).all()
    if portfolios:
        lines.append("### Portfolios")
        for p in portfolios:
            lines.append(f"- {p.name or '(unnamed)'}: initial value {p.initial_portfolio_value}; cashflow allocation {p.cashflow_allocation}")
        lines.append("")

    return "\n".join(lines).strip()


@router.post("/message")
async def send_chat_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    chat_service = get_chat_service()
    plan_context = None
    if request.context == CHAT_CONTEXT_DASHBOARD and request.plan_id is not None:
        plan_context = build_plan_context(request.plan_id, current_user.id, db)

    def generate_stream() -> Generator[str, None, None]:
        try:
            for chunk in chat_service.send_message(
                current_user.id,
                request.message,
                context=request.context,
                plan_id=request.plan_id,
                plan_context=plan_context,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _validate_context(context: str) -> str:
    if context not in (CHAT_CONTEXT_PLAN_BUILDER, CHAT_CONTEXT_DASHBOARD):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"context must be '{CHAT_CONTEXT_PLAN_BUILDER}' or '{CHAT_CONTEXT_DASHBOARD}'",
        )
    return context


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    current_user: User = Depends(get_current_active_user),
    context: str = Query(CHAT_CONTEXT_PLAN_BUILDER, description="Chat context: plan_builder or dashboard"),
    plan_id: Optional[int] = Query(None, description="Plan ID (for dashboard context)"),
):
    """Get the chat history for the current user in the given context."""
    context = _validate_context(context)
    chat_service = get_chat_service()
    history = chat_service.get_chat_history(current_user.id, context=context, plan_id=plan_id)
    messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in history]
    return ChatHistoryResponse(messages=messages)


@router.delete("/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_active_user),
    context: str = Query(CHAT_CONTEXT_PLAN_BUILDER, description="Chat context: plan_builder or dashboard"),
    plan_id: Optional[int] = Query(None, description="Plan ID (for dashboard context)"),
):
    """Clear the chat history for the current user in the given context."""
    context = _validate_context(context)
    chat_service = get_chat_service()
    chat_service.clear_chat_history(current_user.id, context=context, plan_id=plan_id)
    return {"success": True, "message": "Chat history cleared"}


@router.post("/export", response_model=ExportChatResponse)
async def export_chat(
    request: ExportChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    chat_service = get_chat_service()

    try:
        chat_text = chat_service.export_chat_history(
            current_user.id,
            context=request.context,
            plan_id=request.plan_id,
        )

        if not chat_text:
            return ExportChatResponse(
                success=False,
                error="No chat history to export",
            )

        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)

        filename = f"conversation_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = uploads_dir / filename

        filepath.write_text(chat_text, encoding="utf-8")

        if request.trigger_parser:
            try:
                from services.parser_service import ParserService

                parser = ParserService(
                    user_id=current_user.id,
                    filepath=str(filepath),
                    db=db,
                )
                financial_plan, cash_flows, portfolios = parser.extract_data()

                return ExportChatResponse(
                    success=True,
                    chat_text=chat_text,
                    filepath=str(filepath),
                )
            except Exception as parse_error:
                return ExportChatResponse(
                    success=True,
                    chat_text=chat_text,
                    filepath=str(filepath),
                    error=f"Export succeeded but parsing failed: {str(parse_error)}",
                )

        return ExportChatResponse(
            success=True,
            chat_text=chat_text,
            filepath=str(filepath),
        )

    except Exception as e:
        return ExportChatResponse(
            success=False,
            error=str(e),
        )
