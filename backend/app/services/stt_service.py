"""
Speech-to-Text service using faster-whisper
"""
import io
import logging
import struct
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
                # Try to detect CUDA availability without requiring torch
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    # Fallback to CPU if torch is not installed
                    logger.info("torch not installed, using CPU for STT")
                    device = "cpu"
            
            compute_type = "float16" if device == "cuda" else "int8"
            
            logger.info(f"Loading Whisper model: {settings.stt.model_size} on {device}...")
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
            
            # Parse WAV data
            audio_array = self._parse_wav(audio_data)
            
            if audio_array is None or len(audio_array) == 0:
                logger.warning("Empty or invalid audio data")
                return ""
            
            logger.info(f"Audio array shape: {audio_array.shape}, duration: {len(audio_array)/16000:.2f}s")
            
            # Transcribe
            segments, info = model.transcribe(
                audio_array,
                language=lang if lang != "auto" else None,
                beam_size=5
            )
            
            # Combine segments
            text = " ".join([segment.text for segment in segments])
            
            logger.info(f"Transcription result: {text[:100]}..." if len(text) > 100 else f"Transcription result: {text}")
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"STT transcription failed: {e}", exc_info=True)
            raise
    
    def _parse_wav(self, audio_data: bytes) -> Optional[np.ndarray]:
        """Parse WAV data into numpy array"""
        try:
            # Try standard wave module first
            import wave
            
            with io.BytesIO(audio_data) as audio_file:
                with wave.open(audio_file, 'rb') as wav:
                    channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                    sample_rate = wav.getframerate()
                    n_frames = wav.getnframes()
                    frames = wav.readframes(n_frames)
                    
                    logger.info(f"WAV info: channels={channels}, sample_width={sample_width}, "
                               f"sample_rate={sample_rate}, n_frames={n_frames}")
                    
                    if sample_width == 2:  # 16-bit
                        audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    elif sample_width == 4:  # 32-bit
                        audio_array = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
                    else:  # 8-bit or other
                        audio_array = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
                    
                    # Convert to mono if stereo
                    if channels == 2:
                        audio_array = audio_array.reshape(-1, 2).mean(axis=1)
                    
                    # Resample to 16kHz if needed (simple approach)
                    if sample_rate != 16000:
                        # Simple linear interpolation resampling
                        ratio = 16000 / sample_rate
                        new_length = int(len(audio_array) * ratio)
                        indices = np.linspace(0, len(audio_array) - 1, new_length)
                        audio_array = np.interp(indices, np.arange(len(audio_array)), audio_array)
                    
                    return audio_array.astype(np.float32)
                    
        except Exception as e:
            logger.error(f"Failed to parse WAV data: {e}", exc_info=True)
            # Try manual parsing as fallback
            return self._manual_parse_wav(audio_data)
    
    def _manual_parse_wav(self, audio_data: bytes) -> Optional[np.ndarray]:
        """Manually parse WAV data if standard wave module fails"""
        try:
            if len(audio_data) < 44:
                logger.error("Audio data too short for WAV header")
                return None
            
            # Check RIFF header
            if audio_data[:4] != b'RIFF' or audio_data[8:12] != b'WAVE':
                logger.error("Invalid WAV header")
                return None
            
            # Find data chunk
            pos = 12
            while pos < len(audio_data) - 8:
                chunk_id = audio_data[pos:pos+4]
                chunk_size = struct.unpack('<I', audio_data[pos+4:pos+8])[0]
                
                if chunk_id == b'fmt ':
                    fmt_data = audio_data[pos+8:pos+8+chunk_size]
                    audio_format = struct.unpack('<H', fmt_data[0:2])[0]
                    channels = struct.unpack('<H', fmt_data[2:4])[0]
                    sample_rate = struct.unpack('<I', fmt_data[4:8])[0]
                    bits_per_sample = struct.unpack('<H', fmt_data[14:16])[0]
                    logger.info(f"Manual WAV parse: format={audio_format}, channels={channels}, "
                               f"sample_rate={sample_rate}, bits={bits_per_sample}")
                elif chunk_id == b'data':
                    data_start = pos + 8
                    data = audio_data[data_start:data_start+chunk_size]
                    
                    # Convert to float32 array
                    audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    # Convert to mono if stereo
                    if channels == 2:
                        audio_array = audio_array.reshape(-1, 2).mean(axis=1)
                    
                    return audio_array.astype(np.float32)
                
                pos += 8 + chunk_size
            
            logger.error("Could not find data chunk in WAV")
            return None
            
        except Exception as e:
            logger.error(f"Manual WAV parsing failed: {e}", exc_info=True)
            return None
    
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
