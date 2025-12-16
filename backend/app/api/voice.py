"""
Voice API routes - STT, TTS, and WebSocket
"""
import base64
import logging
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, async_session_maker
from app.core.security import get_current_user_token, TokenData, decode_token
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service
from app.services.llm_service import llm_service
from app.services.context_service import context_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user_token)
):
    """Convert speech to text"""
    try:
        audio_data = await audio.read()
        text = await stt_service.transcribe(audio_data)
        return {"text": text}
    except Exception as e:
        logger.error(f"STT failed: {e}")
        raise HTTPException(status_code=500, detail="Speech recognition failed")


@router.post("/tts")
async def text_to_speech(
    text: str,
    current_user: TokenData = Depends(get_current_user_token)
):
    """Convert text to speech"""
    try:
        audio_data = await tts_service.synthesize(text)
        audio_base64 = base64.b64encode(audio_data).decode()
        return {"audio": audio_base64, "format": "wav"}
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail="Speech synthesis failed")


@router.websocket("/ws/{conversation_id}")
async def websocket_voice(websocket: WebSocket, conversation_id: int, token: str):
    """WebSocket endpoint for real-time voice chat"""
    # Verify token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    
    user_id = payload.get("sub")
    
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
    
    await websocket.accept()
    
    try:
        while True:
            # Receive audio data (base64 encoded)
            data = await websocket.receive_json()
            
            if data.get("type") == "audio":
                audio_base64 = data.get("audio", "")
                
                if not audio_base64:
                    continue
                
                try:
                    # Decode audio
                    audio_data = base64.b64decode(audio_base64)
                    
                    # STT
                    await websocket.send_json({"type": "status", "status": "transcribing"})
                    text = await stt_service.transcribe(audio_data)
                    
                    if not text.strip():
                        await websocket.send_json({
                            "type": "error",
                            "message": "No speech detected"
                        })
                        continue
                    
                    await websocket.send_json({
                        "type": "transcription",
                        "text": text
                    })
                    
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
                            content=text,
                            token_count=llm_service.count_tokens(text)
                        )
                        db.add(user_message)
                        await db.commit()
                        await db.refresh(user_message)
                        
                        # Send user message
                        await websocket.send_json({
                            "type": "user_message",
                            "message": {
                                "id": user_message.id,
                                "role": "user",
                                "content": text,
                                "created_at": user_message.created_at.isoformat()
                            }
                        })
                        
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
                            context_summary=conversation.context_summary
                        )
                        
                        # Get AI response
                        await websocket.send_json({"type": "status", "status": "thinking"})
                        
                        full_response = ""
                        async for chunk in llm_service.chat_stream(llm_messages):
                            full_response += chunk
                            await websocket.send_json({
                                "type": "assistant_chunk",
                                "content": chunk
                            })
                        
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
                        
                        # TTS
                        await websocket.send_json({"type": "status", "status": "synthesizing"})
                        
                        try:
                            audio_response = await tts_service.synthesize(full_response)
                            audio_response_base64 = base64.b64encode(audio_response).decode()
                            
                            await websocket.send_json({
                                "type": "assistant_audio",
                                "audio": audio_response_base64,
                                "format": "wav"
                            })
                        except Exception as e:
                            logger.warning(f"TTS failed, sending text only: {e}")
                        
                        # Complete
                        await websocket.send_json({
                            "type": "assistant_complete",
                            "message": {
                                "id": assistant_message.id,
                                "role": "assistant",
                                "content": full_response,
                                "created_at": assistant_message.created_at.isoformat()
                            }
                        })
                
                except Exception as e:
                    logger.error(f"Voice processing error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
