import os
from typing import Generator, List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# System prompt to guide the conversation for gathering financial plan information
SYSTEM_PROMPT = """You are a helpful financial planning assistant. Your goal is to have a natural conversation with the user to gather all the information needed to create a comprehensive financial plan.

You need to gather the following information:
1. Client's name
2. Client's current age
3. Desired retirement age
4. Age to plan until (typically 100)
5. Current portfolio/investment value
6. All sources of income:
   - Source name (e.g., "Salary", "Rental Income")
   - Monthly amount
   - Start age (current age if already receiving)
   - End age (retirement age if not specified)
7. All expenses:
   - Expense name (e.g., "Mortgage", "Groceries")
   - Monthly amount
   - Start age (current age if already paying)
   - End age (100 if not specified)
8. Target portfolio value for retirement (optional for them to provide, but always ask for it.)

Have a friendly, conversational approach. Ask questions naturally and don't overwhelm the user with too many questions at once. Make sure to gather all the required information before concluding the conversation."""


class ChatService:
    """Service for handling chat conversations with OpenAI API."""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        # In-memory storage for chat history: {user_id: [messages]}
        self._chat_histories: Dict[int, List[Dict[str, str]]] = {}
    
    def _get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """Get the message history for a user, including system prompt."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if user_id in self._chat_histories:
            messages.extend(self._chat_histories[user_id])
        
        return messages
    
    def send_message(
        self, 
        user_id: int, 
        user_message: str
    ) -> Generator[str, None, None]:
        """
        Send a user message and stream the assistant's response.
        
        Args:
            user_id: The ID of the user sending the message
            user_message: The message from the user
            
        Yields:
            Chunks of the assistant's response as they arrive
        """
        # Initialize chat history for user if it doesn't exist
        if user_id not in self._chat_histories:
            self._chat_histories[user_id] = []
        
        # Add user message to history
        self._chat_histories[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        # Get full message history including system prompt
        messages = self._get_messages(user_id)
        
        # Stream response from OpenAI
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
        
        # Add assistant response to history after streaming completes
        self._chat_histories[user_id].append({
            "role": "assistant",
            "content": assistant_response
        })
    
    def get_chat_history(self, user_id: int) -> List[Dict[str, str]]:
        """
        Get the chat history for a user (without system prompt).
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of messages in the format [{"role": "user/assistant", "content": "..."}]
        """
        return self._chat_histories.get(user_id, [])
    
    def clear_chat_history(self, user_id: int) -> None:
        """
        Clear the chat history for a user.
        
        Args:
            user_id: The ID of the user
        """
        if user_id in self._chat_histories:
            del self._chat_histories[user_id]
    
    def export_chat_history(self, user_id: int) -> str:
        """
        Export chat history as a text string suitable for saving to a file.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Formatted text string of the conversation
        """
        history = self.get_chat_history(user_id)
        
        if not history:
            return ""
        
        lines = []
        for message in history:
            role = message["role"].capitalize()
            content = message["content"]
            lines.append(f"{role}: {content}\n")
        
        return "".join(lines)

