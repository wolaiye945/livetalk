"""
LLM Service - OpenAI compatible API client for LMStudio
"""
import re
import tiktoken
from typing import List, Dict, Optional, AsyncGenerator
from openai import AsyncOpenAI

from app.core.config import settings


class LLMService:
    """Service for interacting with LLM through OpenAI-compatible API"""
    
    def __init__(self):
        # Main model client
        self.main_client = AsyncOpenAI(
            base_url=settings.llm.main_model.base_url,
            api_key=settings.llm.main_model.api_key
        )
        
        # Summary model client (may be same or different)
        self.summary_client = AsyncOpenAI(
            base_url=settings.llm.summary_model.base_url,
            api_key=settings.llm.summary_model.api_key
        )
        
        # Tokenizer for counting tokens
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
        
        # Pattern to remove <think>...</think> blocks
        self.think_pattern = re.compile(r'<think>.*?</think>', re.DOTALL)
    
    def strip_think_tags(self, text: str) -> str:
        """Remove <think>...</think> blocks from text"""
        result = self.think_pattern.sub('', text)
        return result.strip()
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # Fallback: rough estimate (1 token ≈ 4 chars for English, 1.5 chars for Chinese)
        return len(text) // 2
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count total tokens in messages"""
        total = 0
        for msg in messages:
            total += self.count_tokens(msg.get("content", ""))
            total += 4  # Overhead for role and formatting
        return total
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Send chat completion request to main model"""
        response = await self.main_client.chat.completions.create(
            model=settings.llm.main_model.model,
            messages=messages,
            max_tokens=max_tokens or settings.llm.main_model.max_tokens,
            temperature=temperature or settings.llm.main_model.temperature,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}}
        )
        
        content = response.choices[0].message.content
        return self.strip_think_tags(content)
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Send streaming chat completion request to main model"""
        stream = await self.main_client.chat.completions.create(
            model=settings.llm.main_model.model,
            messages=messages,
            max_tokens=max_tokens or settings.llm.main_model.max_tokens,
            temperature=temperature or settings.llm.main_model.temperature,
            stream=True,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}}
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def summarize(self, text: str, prompt: Optional[str] = None) -> str:
        """Summarize text using summary model"""
        summary_prompt = prompt or settings.context.summary_prompt
        
        messages = [
            {"role": "system", "content": "你是一个擅长总结的助手。请简洁准确地总结对话内容。"},
            {"role": "user", "content": f"{summary_prompt}\n\n{text}"}
        ]
        
        response = await self.summary_client.chat.completions.create(
            model=settings.llm.summary_model.model,
            messages=messages,
            max_tokens=settings.llm.summary_model.max_tokens,
            temperature=settings.llm.summary_model.temperature
        )
        
        return response.choices[0].message.content
    
    async def generate_tags(self, text: str) -> List[str]:
        """Generate tags for conversation"""
        messages = [
            {"role": "system", "content": "你是一个标签生成助手。请为对话生成简洁的标签。"},
            {"role": "user", "content": f"{settings.context.tags_prompt}\n\n{text}"}
        ]
        
        response = await self.summary_client.chat.completions.create(
            model=settings.llm.summary_model.model,
            messages=messages,
            max_tokens=100,
            temperature=0.3
        )
        
        # Parse tags from response
        tags_text = response.choices[0].message.content
        tags = [tag.strip() for tag in tags_text.replace("，", ",").split(",")]
        return [tag for tag in tags if tag][:5]  # Max 5 tags
    
    async def generate_title(self, first_message: str) -> str:
        """Generate title for conversation based on first message"""
        messages = [
            {"role": "system", "content": "根据用户的第一条消息，生成一个简短的对话标题（不超过20个字）。只输出标题，不要其他内容。"},
            {"role": "user", "content": first_message}
        ]
        
        response = await self.summary_client.chat.completions.create(
            model=settings.llm.summary_model.model,
            messages=messages,
            max_tokens=50,
            temperature=0.3
        )
        
        title = response.choices[0].message.content.strip()
        return title[:50] if title else "新对话"


# Global instance
llm_service = LLMService()
