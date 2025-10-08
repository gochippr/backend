from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: List[ChatMessage]

    def latest_user_message(self) -> Optional[ChatMessage]:
        for message in reversed(self.messages):
            if message.role == "user":
                return message
        return None


class ChatResponse(BaseModel):
    reply: str
    context_used: Optional[dict] = None
