"""
Conversation schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ConversationGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class ConversationGroupCreate(ConversationGroupBase):
    pass


class ConversationGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    order_index: Optional[int] = None


class ConversationGroupResponse(ConversationGroupBase):
    id: int
    order_index: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    title: str = Field(default="新对话", max_length=200)


class ConversationCreate(ConversationBase):
    group_id: Optional[int] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    group_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_archived: Optional[bool] = None


class ConversationResponse(ConversationBase):
    id: int
    user_id: int
    group_id: Optional[int]
    tags: List[str]
    summary: Optional[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    id: int
    title: str
    group_id: Optional[int]
    tags: List[str]
    summary: Optional[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationExport(BaseModel):
    id: int
    title: str
    tags: List[str]
    summary: Optional[str]
    created_at: datetime
    messages: List["MessageResponse"]


class BatchDeleteRequest(BaseModel):
    ids: List[int]
