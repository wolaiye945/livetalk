"""
Summary service - handles conversation summarization and tagging
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.message import Message
from app.services.llm_service import llm_service


class SummaryService:
    """Service for generating conversation summaries and tags"""
    
    async def summarize_conversation(
        self,
        db: AsyncSession,
        conversation_id: int,
        generate_tags: bool = True
    ) -> tuple[str, List[str]]:
        """
        Generate summary and tags for a conversation
        
        Returns:
            tuple: (summary, tags)
        """
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return "", []
        
        # Get messages
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        
        if not messages:
            return "", []
        
        # Build conversation text
        conv_text = "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in messages
        ])
        
        # Include context summary if available
        if conversation.context_summary:
            conv_text = f"[之前的对话摘要]\n{conversation.context_summary}\n\n[最近的对话]\n{conv_text}"
        
        # Generate summary
        summary = await llm_service.summarize(conv_text)
        
        # Generate tags if requested
        tags = []
        if generate_tags:
            tags = await llm_service.generate_tags(conv_text)
        
        # Update conversation
        conversation.summary = summary
        if tags:
            conversation.tags = tags
        
        await db.commit()
        
        return summary, tags
    
    async def get_continuation_context(
        self,
        db: AsyncSession,
        conversation_id: int
    ) -> Optional[str]:
        """
        Get context for continuing a conversation
        
        Returns:
            Optional[str]: Context summary for continuation
        """
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return None
        
        # Build continuation context
        context_parts = []
        
        if conversation.summary:
            context_parts.append(f"对话摘要：{conversation.summary}")
        
        if conversation.tags:
            context_parts.append(f"相关主题：{', '.join(conversation.tags)}")
        
        if conversation.context_summary:
            context_parts.append(f"详细上下文：{conversation.context_summary}")
        
        return "\n\n".join(context_parts) if context_parts else None


# Global instance
summary_service = SummaryService()
