import { useRef, useEffect, useCallback } from 'react';

interface AudioPlayerProps {
  audioData: string; // base64 encoded audio
  format?: string;
  autoPlay?: boolean;
  onEnded?: () => void;
}

export default function AudioPlayer({
  audioData,
  format = 'wav',
  autoPlay = true,
  onEnded,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (audioData && audioRef.current) {
      const audioUrl = `data:audio/${format};base64,${audioData}`;
      audioRef.current.src = audioUrl;
      
      if (autoPlay) {
        audioRef.current.play().catch((err) => {
          console.error('Audio playback failed:', err);
        });
      }
    }
  }, [audioData, format, autoPlay]);

  const handleEnded = useCallback(() => {
    onEnded?.();
  }, [onEnded]);

  return (
    <audio
      ref={audioRef}
      onEnded={handleEnded}
      className="hidden"
    />
  );
}

// Hook for playing audio
export function useAudioPlayer() {
  const audioContextRef = useRef<AudioContext | null>(null);

  const playAudio = useCallback(async (base64Data: string) => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }

      const audioContext = audioContextRef.current;
      
      // Resume context if suspended (browser autoplay policy)
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      // Decode base64
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Decode audio
      const audioBuffer = await audioContext.decodeAudioData(bytes.buffer);

      // Play
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start(0);

      return new Promise<void>((resolve) => {
        source.onended = () => resolve();
      });
    } catch (error) {
      console.error('Audio playback error:', error);
      throw error;
    }
  }, []);

  const cleanup = useCallback(() => {
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
  }, []);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return { playAudio, cleanup };
}
