"""
Configuration management for LiveTalk
"""
import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:5173"]


class DatabaseConfig(BaseModel):
    url: str = "sqlite+aiosqlite:///./data/livetalk.db"


class AuthConfig(BaseModel):
    secret_key: str = "livetalk-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440


class LLMModelConfig(BaseModel):
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
    model: str = "default"
    max_tokens: int = 2048
    temperature: float = 0.7


class LLMConfig(BaseModel):
    main_model: LLMModelConfig = LLMModelConfig()
    summary_model: LLMModelConfig = LLMModelConfig(max_tokens=1024, temperature=0.3)
    system_prompt: str = """你是一个友好的语音助手。请遵循以下规则：
1. 直接回答问题，不要输出思考过程（不要使用<think>标签或类似格式）
2. 回复简洁明了，适合语音朗读，避免过长的段落
3. 不要使用markdown格式、代码块或复杂的列表，除非用户明确要求
4. 用自然、口语化的方式表达
5. 如果需要列举，用简短的句子而非符号列表"""


class ContextConfig(BaseModel):
    max_tokens: int = 4096
    compression_threshold: float = 0.8
    summary_prompt: str = "请总结以下对话的要点，保留关键信息，输出简洁的摘要："
    tags_prompt: str = "请为以下对话生成3-5个标签，用逗号分隔："


class STTConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    model_size: str = "base"
    language: str = "zh"
    device: str = "auto"


class TTSConfig(BaseModel):
    model: str = "zh_CN-huayan-medium"
    speaker_id: int = 0
    length_scale: float = 1.0


class VoiceConfig(BaseModel):
    mode: str = "push_to_talk"
    vad_threshold: float = 0.5
    sample_rate: int = 16000


class Settings(BaseSettings):
    server: ServerConfig = ServerConfig()
    database: DatabaseConfig = DatabaseConfig()
    auth: AuthConfig = AuthConfig()
    llm: LLMConfig = LLMConfig()
    context: ContextConfig = ContextConfig()
    stt: STTConfig = STTConfig()
    tts: TTSConfig = TTSConfig()
    voice: VoiceConfig = VoiceConfig()

    class Config:
        env_file = ".env"


def load_config(config_path: Optional[str] = None) -> Settings:
    """Load configuration from YAML file"""
    if config_path is None:
        # Default config path
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_path = base_dir / "config.yaml"
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        return Settings(**config_data)
    
    return Settings()


# Global settings instance
settings = load_config()
