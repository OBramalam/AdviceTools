import os
from pathlib import Path
from typing import Generator, List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# System prompt for the plan-builder flow (gathering financial plan information)
PLAN_BUILDER_SYSTEM_PROMPT = """You are a helpful financial planning assistant. Your goal is to have a natural conversation with the user to gather all the information needed to create a comprehensive financial plan.

You need to gather the following information:
1. Client/plan name
2. Client's current age (can be a decimal, e.g., 35.5)
3. Desired retirement age (can be a decimal)
4. Age to plan until (default to 100, can be a decimal)
5. All sources of income - for each income source, gather:
   - Source name (e.g., "Salary", "Rental Income")
   - Amount (cash flow amount)
   - Frequency: How often the expense is paid (e.g., monthly, quarterly, annually, every 3 years, one-off, etc)
   - Start age (current age if already receiving, can be a decimal)
   - End age (retirement age if not specified, can be a decimal)
6. All expenses - for each expense, gather:
   - Expense name (e.g., "Mortgage", "Groceries")
   - Amount (cash flow amount)
   - Frequency: How often the expense is paid (e.g., monthly, quarterly, annually, every 3 years, one-off, etc)
   - Start age (current age if already paying, can be a decimal)
   - End age (100 if not specified, can be a decimal)
7. All portfolios - for each portfolio, gather:
   - Portfolio name
   - Initial portfolio value (nominal dollar value of initial wealth allocated to this portfolio)

Have a friendly, conversational approach. Ask questions naturally and don't overwhelm the user with 
too many questions at once. This is especially important for income and expense sections, where ther
are a lot of details to gather for each item. The general pattern for collecting this information 
should be:

1. Ask for all of their regular income/expense items, specifically say for the best results these should be
monthly amounts. At first we just ask for the name and amount, then once we have these, we can ask them to confirm
thhat these are monthly incomes/expenses, giving them the opportunity to specify otherwise.
2. We can then say that we will assume these cashflows will start now and go until retirement age, asking
them to confirm or let us know if this is not the case for any of these items.
3. At this point we can ask for any one-off incomes/expenses that they expect, such as tuition, house deposit, etc. 

Make sure to gather all the required information before concluding the conversation and instructing 
the user to press the 'Export and parse' button."""

# Backward compatibility alias
SYSTEM_PROMPT = PLAN_BUILDER_SYSTEM_PROMPT

CHAT_CONTEXT_PLAN_BUILDER = "plan_builder"
CHAT_CONTEXT_DASHBOARD = "dashboard"


def _history_key(user_id: int, context: str, plan_id: Optional[int]) -> str:
    """Return a string key for chat history storage."""
    return f"{user_id}:{context}:{plan_id or ''}"


def _load_dashboard_ui_doc() -> str:
    """Load the dashboard interface documentation from docs/AI_HELPER_SYSTEM_PROMPT.md."""
    base = Path(__file__).resolve().parent.parent
    path = base / "docs" / "AI_HELPER_SYSTEM_PROMPT.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _build_dashboard_system_prompt(plan_context: Optional[str]) -> str:
    """Build the system prompt for the dashboard assistant (UI doc + optional plan context)."""
    ui_doc = _load_dashboard_ui_doc()
    if not ui_doc.strip():
        ui_doc = "You are a helpful AI assistant for a Financial Planning web application. Guide users through the interface and help them use the application."
    if plan_context and plan_context.strip():
        return f"{ui_doc.strip()}\n\n## Current plan context\n\nUse the following plan details to answer questions about the user's plan. Do not invent data.\n\n{plan_context.strip()}"
    return ui_doc.strip()


class ChatService:
    """Service for handling chat conversations with OpenAI API."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")

        # In-memory storage: key = _history_key(user_id, context, plan_id), value = list of messages
        self._chat_histories: Dict[str, List[Dict[str, str]]] = {}

    def _get_system_prompt(self, context: str, plan_context: Optional[str]) -> str:
        if context == CHAT_CONTEXT_DASHBOARD:
            return _build_dashboard_system_prompt(plan_context)
        return PLAN_BUILDER_SYSTEM_PROMPT

    def _get_messages(
        self,
        user_id: int,
        context: str,
        plan_id: Optional[int],
        plan_context: Optional[str],
    ) -> List[Dict[str, str]]:
        """Get the message history for a user/context/plan, including system prompt."""
        system_prompt = self._get_system_prompt(context, plan_context)
        messages = [{"role": "system", "content": system_prompt}]
        key = _history_key(user_id, context, plan_id)
        if key in self._chat_histories:
            messages.extend(self._chat_histories[key])
        return messages

    def send_message(
        self,
        user_id: int,
        user_message: str,
        context: str = CHAT_CONTEXT_PLAN_BUILDER,
        plan_id: Optional[int] = None,
        plan_context: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Send a user message and stream the assistant's response.

        Args:
            user_id: The ID of the user sending the message
            user_message: The message from the user
            context: One of "plan_builder" or "dashboard"
            plan_id: Optional plan ID (for dashboard context, used for history key)
            plan_context: Optional pre-formatted plan details string (for dashboard, injected into system prompt)

        Yields:
            Chunks of the assistant's response as they arrive
        """
        key = _history_key(user_id, context, plan_id)
        if key not in self._chat_histories:
            self._chat_histories[key] = []

        self._chat_histories[key].append({"role": "user", "content": user_message})

        messages = self._get_messages(user_id, context, plan_id, plan_context)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.7,
        )

        assistant_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                assistant_response += content
                yield content

        self._chat_histories[key].append(
            {"role": "assistant", "content": assistant_response}
        )

    def get_chat_history(
        self,
        user_id: int,
        context: str = CHAT_CONTEXT_PLAN_BUILDER,
        plan_id: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        Get the chat history for a user in the given context (without system prompt).

        Args:
            user_id: The ID of the user
            context: One of "plan_builder" or "dashboard"
            plan_id: Optional plan ID (for dashboard context)

        Returns:
            List of messages in the format [{"role": "user/assistant", "content": "..."}]
        """
        key = _history_key(user_id, context, plan_id)
        return self._chat_histories.get(key, [])

    def clear_chat_history(
        self,
        user_id: int,
        context: str = CHAT_CONTEXT_PLAN_BUILDER,
        plan_id: Optional[int] = None,
    ) -> None:
        """
        Clear the chat history for a user in the given context.

        Args:
            user_id: The ID of the user
            context: One of "plan_builder" or "dashboard"
            plan_id: Optional plan ID (for dashboard context)
        """
        key = _history_key(user_id, context, plan_id)
        if key in self._chat_histories:
            del self._chat_histories[key]

    def export_chat_history(
        self,
        user_id: int,
        context: str = CHAT_CONTEXT_PLAN_BUILDER,
        plan_id: Optional[int] = None,
    ) -> str:
        """
        Export chat history as a text string suitable for saving to a file.

        Args:
            user_id: The ID of the user
            context: One of "plan_builder" or "dashboard"
            plan_id: Optional plan ID (for dashboard context)

        Returns:
            Formatted text string of the conversation
        """
        history = self.get_chat_history(user_id, context, plan_id)
        if not history:
            return ""
        lines = []
        for message in history:
            role = message["role"].capitalize()
            content = message["content"]
            lines.append(f"{role}: {content}\n")
        return "".join(lines)
