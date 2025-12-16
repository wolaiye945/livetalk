"""
Speech-to-Text service using faster-whisper
"""
import io
import logging
from typing import Optional
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy load whisper model
_whisper_model = None


def get_whisper_model():
    """Get or initialize whisper model"""
    global _whisper_model
    
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            
            device = settings.stt.device
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            compute_type = "float16" if device == "cuda" else "int8"
            
            _whisper_model = WhisperModel(
                settings.stt.model_size,
                device=device,
                compute_type=compute_type
            )
            logger.info(f"Whisper model loaded: {settings.stt.model_size} on {device}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    return _whisper_model


class STTService:
    """Speech-to-Text service using faster-whisper"""
    
    def __init__(self):
        self.language = settings.stt.language
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio to text
        
        Args:
            audio_data: Audio bytes (WAV format)
            language: Language code (default from config)
        
        Returns:
            Transcribed text
        """
        try:
            model = get_whisper_model()
            lang = language or self.language
            
            # Convert bytes to numpy array
            import wave
            
            with io.BytesIO(audio_data) as audio_file:
                with wave.open(audio_file, 'rb') as wav:
                    frames = wav.readframes(wav.getnframes())
                    audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe
            segments, info = model.transcribe(
                audio_array,
                language=lang if lang != "auto" else None,
                beam_size=5
            )
            
            # Combine segments
            text = " ".join([segment.text for segment in segments])
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"STT transcription failed: {e}")
            raise
    
    async def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None
    ) -> str:
        """Transcribe audio file to text"""
        with open(file_path, "rb") as f:
            audio_data = f.read()
        return await self.transcribe(audio_data, language)


# Global instance
stt_service = STTService()
