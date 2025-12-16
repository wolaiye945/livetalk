"""
Admin API routes
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.core.database import get_db
from app.core.security import require_admin, TokenData
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.user import UserResponse
from app.schemas.conversation import ConversationListResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.get("/users/{user_id}/conversations", response_model=List[ConversationListResponse])
async def list_user_conversations(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List user's conversations (admin only)"""
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()
    
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


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete user and all their data (admin only)"""
    # Cannot delete self
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted"}


@router.get("/stats")
async def get_stats(
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics (admin only)"""
    # Count users
    result = await db.execute(select(func.count(User.id)))
    user_count = result.scalar()
    
    # Count conversations
    result = await db.execute(select(func.count(Conversation.id)))
    conversation_count = result.scalar()
    
    # Count messages
    result = await db.execute(select(func.count(Message.id)))
    message_count = result.scalar()
    
    return {
        "users": user_count,
        "conversations": conversation_count,
        "messages": message_count
    }
