"""
Conversation API routes
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user_token, TokenData
from app.models.conversation import Conversation, ConversationGroup
from app.models.message import Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    ConversationGroupCreate,
    ConversationGroupUpdate,
    ConversationGroupResponse,
    BatchDeleteRequest
)
from app.services.summary_service import summary_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=List[ConversationListResponse])
async def list_conversations(
    group_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_archived: Optional[bool] = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """List user's conversations"""
    query = select(Conversation).where(Conversation.user_id == current_user.user_id)
    
    # Filters
    if group_id is not None:
        query = query.where(Conversation.group_id == group_id)
    
    if is_archived is not None:
        query = query.where(Conversation.is_archived == is_archived)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Conversation.title.ilike(search_pattern),
                Conversation.summary.ilike(search_pattern)
            )
        )
    
    # Order and pagination
    query = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Get message counts
    response = []
    for conv in conversations:
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        )
        message_count = count_result.scalar()
        
        response.append(ConversationListResponse(
            id=conv.id,
            title=conv.title,
            group_id=conv.group_id,
            tags=conv.tags or [],
            summary=conv.summary,
            is_archived=conv.is_archived,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=message_count
        ))
    
    return response


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation"""
    # Verify group ownership if provided
    if data.group_id:
        result = await db.execute(
            select(ConversationGroup).where(
                ConversationGroup.id == data.group_id,
                ConversationGroup.user_id == current_user.user_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Group not found")
    
    conversation = Conversation(
        user_id=current_user.user_id,
        title=data.title,
        group_id=data.group_id,
        tags=[]
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation details"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Update conversation"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update fields
    if data.title is not None:
        conversation.title = data.title
    if data.group_id is not None:
        conversation.group_id = data.group_id if data.group_id > 0 else None
    if data.tags is not None:
        conversation.tags = data.tags
    if data.is_archived is not None:
        conversation.is_archived = data.is_archived
    
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Delete conversation"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await db.delete(conversation)
    await db.commit()


@router.delete("/batch", status_code=status.HTTP_204_NO_CONTENT)
async def batch_delete_conversations(
    data: BatchDeleteRequest,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Batch delete conversations"""
    await db.execute(
        delete(Conversation).where(
            Conversation.id.in_(data.ids),
            Conversation.user_id == current_user.user_id
        )
    )
    await db.commit()


@router.post("/{conversation_id}/summarize")
async def summarize_conversation(
    conversation_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Generate summary and tags for conversation"""
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    summary, tags = await summary_service.summarize_conversation(db, conversation_id)
    
    return {"summary": summary, "tags": tags}


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: int,
    format: str = Query("json", enum=["json", "markdown"]),
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Export conversation"""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if format == "markdown":
        # Export as Markdown
        md_content = f"# {conversation.title}\n\n"
        md_content += f"**创建时间**: {conversation.created_at}\n\n"
        
        if conversation.tags:
            md_content += f"**标签**: {', '.join(conversation.tags)}\n\n"
        
        if conversation.summary:
            md_content += f"**摘要**: {conversation.summary}\n\n"
        
        md_content += "---\n\n"
        
        for msg in conversation.messages:
            role_name = "👤 用户" if msg.role == "user" else "🤖 助手"
            md_content += f"### {role_name}\n\n{msg.content}\n\n"
        
        return {"content": md_content, "filename": f"{conversation.title}.md"}
    
    else:
        # Export as JSON
        export_data = {
            "id": conversation.id,
            "title": conversation.title,
            "tags": conversation.tags,
            "summary": conversation.summary,
            "created_at": conversation.created_at.isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in conversation.messages
            ]
        }
        return export_data
