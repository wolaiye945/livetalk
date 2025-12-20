"""
Text-to-Speech service using Piper TTS
"""
import io
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import wave

from app.core.config import settings

logger = logging.getLogger(__name__)

# Model directory
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "piper"


class TTSService:
    """Text-to-Speech service using Piper TTS"""
    
    def __init__(self):
        self.model = settings.tts.model
        self.speaker_id = settings.tts.speaker_id
        self.length_scale = settings.tts.length_scale
        self._piper_path = None
    
    def _get_piper_path(self) -> Optional[str]:
        """Get path to piper executable"""
        if self._piper_path:
            return self._piper_path
        
        # Try to find piper in PATH
        import shutil
        piper = shutil.which("piper")
        if piper:
            self._piper_path = piper
            return piper
        
        # Check in models directory
        piper_exe = MODELS_DIR / "piper.exe"
        if piper_exe.exists():
            self._piper_path = str(piper_exe)
            return self._piper_path
        
        return None
    
    async def synthesize(
        self,
        text: str,
        output_format: str = "wav"
    ) -> bytes:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            output_format: Output format (wav)
        
        Returns:
            Audio bytes
        """
        try:
            # Try using piper-tts Python package first
            try:
                from piper import PiperVoice
                from piper.config import SynthesisConfig
                
                model_path = MODELS_DIR / f"{self.model}.onnx"
                config_path = MODELS_DIR / f"{self.model}.onnx.json"
                
                if not model_path.exists():
                    raise FileNotFoundError(f"Piper model not found: {model_path}")
                
                voice = PiperVoice.load(str(model_path), str(config_path))
                
                # Create synthesis config
                config = SynthesisConfig(
                    speaker_id=self.speaker_id,
                    length_scale=self.length_scale
                )
                
                # Synthesize to WAV
                audio_buffer = io.BytesIO()
                with wave.open(audio_buffer, "wb") as wav_file:
                    voice.synthesize_wav(text, wav_file, syn_config=config)
                
                return audio_buffer.getvalue()
            
            except ImportError:
                # Fall back to command line piper
                return await self._synthesize_cli(text)
        
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise
    
    async def _synthesize_cli(self, text: str) -> bytes:
        """Synthesize using command line piper"""
        piper_path = self._get_piper_path()
        
        if not piper_path:
            raise RuntimeError("Piper TTS not installed")
        
        model_path = MODELS_DIR / f"{self.model}.onnx"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Piper model not found: {model_path}")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name
        
        try:
            # Run piper
            process = subprocess.run(
                [
                    piper_path,
                    "--model", str(model_path),
                    "--output_file", output_path,
                    "--speaker", str(self.speaker_id),
                    "--length_scale", str(self.length_scale)
                ],
                input=text.encode("utf-8"),
                capture_output=True
            )
            
            if process.returncode != 0:
                raise RuntimeError(f"Piper failed: {process.stderr.decode()}")
            
            # Read output
            with open(output_path, "rb") as f:
                return f.read()
        
        finally:
            # Cleanup
            Path(output_path).unlink(missing_ok=True)
    
    async def synthesize_to_file(
        self,
        text: str,
        output_path: str
    ) -> str:
        """Synthesize speech to file"""
        audio_data = await self.synthesize(text)
        
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        return output_path


# Global instance
tts_service = TTSService()
