"""
Message schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    content: str = Field(..., min_length=1)
    role: str = Field(default="user")


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    audio_path: Optional[str]
    token_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1)
    

class ChatResponse(BaseModel):
    message: MessageResponse
    assistant_message: MessageResponse
