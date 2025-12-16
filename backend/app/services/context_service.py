"""
Context management service - handles context compression
"""
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.llm_service import llm_service


class ContextService:
    """Service for managing conversation context and compression"""
    
    def __init__(self):
        self.max_tokens = settings.context.max_tokens
        self.threshold = settings.context.compression_threshold
    
    def build_messages(
        self,
        messages: List[Message],
        context_summary: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build message list for LLM from database messages"""
        result = []
        
        # Add system prompt if provided
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        
        # Add context summary if available (from previous compression)
        if context_summary:
            result.append({
                "role": "system",
                "content": f"以下是之前对话的摘要：\n{context_summary}"
            })
        
        # Add messages
        for msg in messages:
            result.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return result
    
    def needs_compression(self, messages: List[Dict[str, str]]) -> bool:
        """Check if context needs compression"""
        total_tokens = llm_service.count_messages_tokens(messages)
        threshold_tokens = int(self.max_tokens * self.threshold)
        return total_tokens > threshold_tokens
    
    async def compress_context(
        self,
        messages: List[Message],
        keep_recent: int = 4
    ) -> tuple[str, List[Message]]:
        """
        Compress context by summarizing older messages
        
        Returns:
            tuple: (summary of old messages, list of recent messages to keep)
        """
        if len(messages) <= keep_recent:
            return "", messages
        
        # Split messages: old ones to summarize, recent ones to keep
        old_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]
        
        # Build text to summarize
        summary_text = "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in old_messages
        ])
        
        # Generate summary
        summary = await llm_service.summarize(summary_text)
        
        return summary, recent_messages
    
    async def update_conversation_context(
        self,
        db: AsyncSession,
        conversation_id: int
    ) -> Optional[str]:
        """
        Check and compress conversation context if needed
        
        Returns:
            Optional[str]: New context summary if compression happened
        """
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return None
        
        # Get messages
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        
        # Build current context
        current_messages = self.build_messages(
            messages,
            context_summary=conversation.context_summary
        )
        
        # Check if compression needed
        if not self.needs_compression(current_messages):
            return None
        
        # Compress
        summary, recent = await self.compress_context(list(messages))
        
        # Combine with existing summary
        if conversation.context_summary:
            full_summary = f"{conversation.context_summary}\n\n{summary}"
            # If combined summary is too long, summarize it again
            if llm_service.count_tokens(full_summary) > self.max_tokens // 2:
                full_summary = await llm_service.summarize(full_summary)
        else:
            full_summary = summary
        
        # Update conversation
        conversation.context_summary = full_summary
        
        # Delete old messages, keep only recent ones
        recent_ids = [m.id for m in recent]
        for msg in messages:
            if msg.id not in recent_ids:
                await db.delete(msg)
        
        await db.commit()
        
        return full_summary


# Global instance
context_service = ContextService()
