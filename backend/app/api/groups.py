"""
Conversation groups API routes
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_token, TokenData
from app.models.conversation import ConversationGroup
from app.schemas.conversation import (
    ConversationGroupCreate,
    ConversationGroupUpdate,
    ConversationGroupResponse
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=List[ConversationGroupResponse])
async def list_groups(
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """List user's conversation groups"""
    result = await db.execute(
        select(ConversationGroup)
        .where(ConversationGroup.user_id == current_user.user_id)
        .order_by(ConversationGroup.order_index, ConversationGroup.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=ConversationGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: ConversationGroupCreate,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation group"""
    # Get max order_index
    result = await db.execute(
        select(ConversationGroup.order_index)
        .where(ConversationGroup.user_id == current_user.user_id)
        .order_by(ConversationGroup.order_index.desc())
        .limit(1)
    )
    max_order = result.scalar() or 0
    
    group = ConversationGroup(
        user_id=current_user.user_id,
        name=data.name,
        order_index=max_order + 1
    )
    
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return group


@router.put("/{group_id}", response_model=ConversationGroupResponse)
async def update_group(
    group_id: int,
    data: ConversationGroupUpdate,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Update conversation group"""
    result = await db.execute(
        select(ConversationGroup).where(
            ConversationGroup.id == group_id,
            ConversationGroup.user_id == current_user.user_id
        )
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if data.name is not None:
        group.name = data.name
    if data.order_index is not None:
        group.order_index = data.order_index
    
    await db.commit()
    await db.refresh(group)
    
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Delete conversation group (conversations will be ungrouped)"""
    result = await db.execute(
        select(ConversationGroup).where(
            ConversationGroup.id == group_id,
            ConversationGroup.user_id == current_user.user_id
        )
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    await db.delete(group)
    await db.commit()
