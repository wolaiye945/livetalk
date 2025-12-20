"""
Chat API routes - messages and WebSocket
"""
import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db, async_session_maker
from app.core.security import get_current_user_token, TokenData, decode_token
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageResponse, ChatRequest, ChatResponse
from app.services.llm_service import llm_service
from app.services.context_service import context_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """List messages in a conversation"""
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.user_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: int,
    data: ChatRequest,
    current_user: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get AI response"""
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
    
    # Create user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=data.content,
        token_count=llm_service.count_tokens(data.content)
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)
    
    # Update title if first message
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id)
    )
    messages = result.scalars().all()
    
    if len(messages) == 1 and conversation.title == "新对话":
        try:
            new_title = await llm_service.generate_title(data.content)
            conversation.title = new_title
        except Exception as e:
            logger.warning(f"Failed to generate title: {e}")
    
    # Check if context compression is needed
    await context_service.update_conversation_context(db, conversation_id)
    
    # Build messages for LLM
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    llm_messages = context_service.build_messages(
        messages,
        context_summary=conversation.context_summary,
        system_prompt=settings.llm.system_prompt
    )
    
    # Get AI response
    try:
        response_content = await llm_service.chat(llm_messages)
    except Exception as e:
        logger.error(f"LLM chat failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AI response")
    
    # Create assistant message
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=response_content,
        token_count=llm_service.count_tokens(response_content)
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    
    return ChatResponse(
        message=user_message,
        assistant_message=assistant_message
    )


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, conversation_id: int):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, conversation_id: int):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
    
    async def send_json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)


manager = ConnectionManager()


@router.websocket("/ws/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: int, token: str):
    """WebSocket endpoint for real-time chat"""
    # Verify token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    
    # user_id is stored as string in token, convert to int
    user_id = int(payload.get("sub")) if payload.get("sub") else None
    
    if user_id is None:
        await websocket.close(code=4001)
        return
    
    # Verify conversation ownership
    async with async_session_maker() as db:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            await websocket.close(code=4004)
            return
    
    await manager.connect(websocket, conversation_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_content = data.get("content", "")
            
            if not message_content:
                continue
            
            async with async_session_maker() as db:
                # Get conversation
                result = await db.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                conversation = result.scalar_one_or_none()
                
                # Save user message
                user_message = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=message_content,
                    token_count=llm_service.count_tokens(message_content)
                )
                db.add(user_message)
                await db.commit()
                await db.refresh(user_message)
                
                # Send user message confirmation
                await manager.send_json({
                    "type": "user_message",
                    "message": {
                        "id": user_message.id,
                        "role": "user",
                        "content": message_content,
                        "created_at": user_message.created_at.isoformat()
                    }
                }, websocket)
                
                # Check context compression
                await context_service.update_conversation_context(db, conversation_id)
                
                # Get messages
                result = await db.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at)
                )
                messages = result.scalars().all()
                
                # Build LLM messages
                llm_messages = context_service.build_messages(
                    messages,
                    context_summary=conversation.context_summary,
                    system_prompt=settings.llm.system_prompt
                )
                
                # Stream AI response
                full_response = ""
                
                try:
                    async for chunk in llm_service.chat_stream(llm_messages):
                        full_response += chunk
                        await manager.send_json({
                            "type": "assistant_chunk",
                            "content": chunk
                        }, websocket)
                            
                except Exception as e:
                    logger.error(f"Streaming failed: {e}")
                    await manager.send_json({
                        "type": "error",
                        "message": str(e)
                    }, websocket)
                    continue
                
                # Save assistant message
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    token_count=llm_service.count_tokens(full_response)
                )
                db.add(assistant_message)
                await db.commit()
                await db.refresh(assistant_message)
                
                # Send completion
                await manager.send_json({
                    "type": "assistant_complete",
                    "message": {
                        "id": assistant_message.id,
                        "role": "assistant",
                        "content": full_response,
                        "created_at": assistant_message.created_at.isoformat()
                    }
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, conversation_id)
