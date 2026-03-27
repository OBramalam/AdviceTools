import os
from pathlib import Path
from typing import Generator, List, Dict, Optional, TYPE_CHECKING
from dotenv import load_dotenv
from openai import OpenAI

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

load_dotenv()

# Shared plan-builder core (all jurisdictions)
PLAN_BUILDER_CORE_PROMPT = """You are a helpful financial planning assistant. Your goal is to have a natural conversation with the user to gather all the information needed to create a comprehensive financial plan.

You need to gather the following information:
1. Client/plan name
2. Client's current age (int)
3. Desired retirement age (int)
4. Age to plan until (default to 100, int.)
5. All sources of income - for each income source, gather:
   - Source name (e.g., "Salary", "Rental Income")
   - Amount (cash flow amount)
   - Frequency: How often the expense is paid (e.g., monthly, quarterly, annually, every 3 years, one-off, etc)
   - Start age (current age if already receiving, int)
   - End age (retirement age if not specified, int.)
6. All expenses - for each expense, gather:
   - Expense name (e.g., "Mortgage", "Groceries")
   - Amount (cash flow amount)
   - Frequency: How often the expense is paid (e.g., monthly, quarterly, annually, every 3 years, one-off, etc)
   - Start age (current age if already paying, int)
   - End age (100 if not specified, int)
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

# New Zealand — aligns with NZ extraction (KiwiSaver linked to portfolio names)
PLAN_BUILDER_NZ_APPENDIX = """

## New Zealand (KiwiSaver)

The downstream parser expects KiwiSaver details tied to **portfolio names** that already appear in the portfolios list.

After you have portfolios and income sources named clearly, for **each KiwiSaver account** (each distinct KiwiSaver balance or scheme the client holds as a separate portfolio):

1. Confirm which **portfolio name** in the list is the KiwiSaver bucket (the name must match exactly later).
2. **Employee** KiwiSaver contribution rate as a percentage of the relevant income (e.g. 3, 4, 6, 8, 10).
3. **Employer** contribution rate as a percentage (or what the client knows, e.g. employer matches 3%).
4. Which **single income source name** the contributions are based on (must match the income name you gathered earlier, e.g. "Salary").

If the client has no KiwiSaver or you do not need it for the plan, you may still list portfolios without KiwiSaver — omit extra KiwiSaver detail only when clearly not applicable. Use the same currency and terminology (NZD, KiwiSaver) the client uses."""

# Australia — placeholder for future super-specific extraction; currently same structure as base
PLAN_BUILDER_AU_APPENDIX = """

## Australia (superannuation)

Where relevant, ask about employer super contributions (e.g. SG rate) and any salary sacrifice; note portfolio names clearly so they can be matched to investment buckets later."""


def _plan_builder_jurisdiction_suffix(jurisdiction_key: str) -> str:
    """Return a stable segment for chat history keys (nz, au, default)."""
    if jurisdiction_key == "nz":
        return "nz"
    if jurisdiction_key == "au":
        return "au"
    return "default"


def build_plan_builder_system_prompt(jurisdiction_key: str) -> str:
    """Core + jurisdiction-specific appendix. Same routing idea as ParserService (tax_jurisdiction)."""
    core = PLAN_BUILDER_CORE_PROMPT.strip()
    if jurisdiction_key == "nz":
        return f"{core}{PLAN_BUILDER_NZ_APPENDIX}"
    if jurisdiction_key == "au":
        return f"{core}{PLAN_BUILDER_AU_APPENDIX}"
    return core


def resolve_plan_builder_jurisdiction_key(user_id: int, db: "Session") -> str:
    """Aligns with parser: adviser `tax_jurisdiction` → nz, au, or default."""
    from common.utils import get_adviser_config_by_user_id

    ac = get_adviser_config_by_user_id(user_id, db)
    j = (ac.tax_jurisdiction or "").strip().lower()
    if j == "nz":
        return "nz"
    if j == "au":
        return "au"
    return "default"


# Backward compatibility: default / generic plan builder prompt
PLAN_BUILDER_SYSTEM_PROMPT = build_plan_builder_system_prompt("default")
SYSTEM_PROMPT = PLAN_BUILDER_SYSTEM_PROMPT

CHAT_CONTEXT_PLAN_BUILDER = "plan_builder"
CHAT_CONTEXT_DASHBOARD = "dashboard"


def _history_key(
    user_id: int,
    context: str,
    plan_id: Optional[int],
    plan_builder_jurisdiction_key: Optional[str] = None,
) -> str:
    """Return a string key for chat history storage.

    plan_builder_jurisdiction_key isolates threads when adviser tax_jurisdiction changes (nz / au / default).
    """
    base = f"{user_id}:{context}:{plan_id or ''}"
    if context == CHAT_CONTEXT_PLAN_BUILDER:
        suffix = _plan_builder_jurisdiction_suffix(plan_builder_jurisdiction_key or "default")
        return f"{base}:{suffix}"
    return base


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

        # In-memory storage: key = _history_key(...), value = list of messages
        self._chat_histories: Dict[str, List[Dict[str, str]]] = {}

    def _get_system_prompt(
        self,
        context: str,
        plan_context: Optional[str],
        plan_builder_jurisdiction_key: Optional[str] = None,
    ) -> str:
        if context == CHAT_CONTEXT_DASHBOARD:
            return _build_dashboard_system_prompt(plan_context)
        jk = plan_builder_jurisdiction_key or "default"
        return build_plan_builder_system_prompt(jk)

    def _get_messages(
        self,
        user_id: int,
        context: str,
        plan_id: Optional[int],
        plan_context: Optional[str],
        plan_builder_jurisdiction_key: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Get the message history for a user/context/plan, including system prompt."""
        system_prompt = self._get_system_prompt(
            context, plan_context, plan_builder_jurisdiction_key
        )
        messages = [{"role": "system", "content": system_prompt}]
        key = _history_key(user_id, context, plan_id, plan_builder_jurisdiction_key)
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
        plan_builder_jurisdiction_key: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Send a user message and stream the assistant's response.

        Args:
            user_id: The ID of the user sending the message
            user_message: The message from the user
            context: One of "plan_builder" or "dashboard"
            plan_id: Optional plan ID (for dashboard context, used for history key)
            plan_context: Optional pre-formatted plan details string (for dashboard, injected into system prompt)
            plan_builder_jurisdiction_key: For plan_builder only: "nz", "au", or "default" (from adviser tax_jurisdiction).

        Yields:
            Chunks of the assistant's response as they arrive
        """
        key = _history_key(user_id, context, plan_id, plan_builder_jurisdiction_key)
        if key not in self._chat_histories:
            self._chat_histories[key] = []

        self._chat_histories[key].append({"role": "user", "content": user_message})

        messages = self._get_messages(
            user_id, context, plan_id, plan_context, plan_builder_jurisdiction_key
        )

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
        plan_builder_jurisdiction_key: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Get the chat history for a user in the given context (without system prompt).

        Args:
            user_id: The ID of the user
            context: One of "plan_builder" or "dashboard"
            plan_id: Optional plan ID (for dashboard context)
            plan_builder_jurisdiction_key: For plan_builder, must match send_message / export.

        Returns:
            List of messages in the format [{"role": "user/assistant", "content": "..."}]
        """
        key = _history_key(user_id, context, plan_id, plan_builder_jurisdiction_key)
        return self._chat_histories.get(key, [])

    def clear_chat_history(
        self,
        user_id: int,
        context: str = CHAT_CONTEXT_PLAN_BUILDER,
        plan_id: Optional[int] = None,
        plan_builder_jurisdiction_key: Optional[str] = None,
    ) -> None:
        """
        Clear the chat history for a user in the given context.

        Args:
            user_id: The ID of the user
            context: One of "plan_builder" or "dashboard"
            plan_id: Optional plan ID (for dashboard context)
            plan_builder_jurisdiction_key: For plan_builder, must match send_message.
        """
        key = _history_key(user_id, context, plan_id, plan_builder_jurisdiction_key)
        if key in self._chat_histories:
            del self._chat_histories[key]

    def export_chat_history(
        self,
        user_id: int,
        context: str = CHAT_CONTEXT_PLAN_BUILDER,
        plan_id: Optional[int] = None,
        plan_builder_jurisdiction_key: Optional[str] = None,
    ) -> str:
        """
        Export chat history as a text string suitable for saving to a file.

        Args:
            user_id: The ID of the user
            context: One of "plan_builder" or "dashboard"
            plan_id: Optional plan ID (for dashboard context)
            plan_builder_jurisdiction_key: For plan_builder, must match send_message.

        Returns:
            Formatted text string of the conversation
        """
        history = self.get_chat_history(
            user_id, context, plan_id, plan_builder_jurisdiction_key
        )
        if not history:
            return ""
        lines = []
        for message in history:
            role = message["role"].capitalize()
            content = message["content"]
            lines.append(f"{role}: {content}\n")
        return "".join(lines)
