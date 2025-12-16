import { useState, useRef, useCallback, useEffect } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { authService } from '@/services/authService';
import clsx from 'clsx';

interface VoiceRecorderProps {
  conversationId: number;
  onTranscription: (text: string) => void;
  disabled?: boolean;
}

type RecordingStatus = 'idle' | 'recording' | 'processing';

export default function VoiceRecorder({
  conversationId,
  onTranscription,
  disabled,
}: VoiceRecorderProps) {
  const [status, setStatus] = useState<RecordingStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        if (chunksRef.current.length === 0) {
          setStatus('idle');
          return;
        }

        setStatus('processing');

        try {
          // Create blob from chunks
          const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
          
          // Convert to WAV for better compatibility with Whisper
          const wavBlob = await convertToWav(audioBlob);

          // Send to server for STT
          const formData = new FormData();
          formData.append('audio', wavBlob, 'recording.wav');

          const response = await fetch('/api/voice/stt', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${authService.getToken()}`,
            },
            body: formData,
          });

          if (!response.ok) {
            throw new Error('语音识别失败');
          }

          const data = await response.json();
          
          if (data.text && data.text.trim()) {
            onTranscription(data.text.trim());
          } else {
            setError('未检测到语音');
          }
        } catch (err) {
          console.error('STT error:', err);
          setError('语音识别失败');
        } finally {
          setStatus('idle');
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100); // Collect data every 100ms
      setStatus('recording');
    } catch (err) {
      console.error('Microphone access error:', err);
      setError('无法访问麦克风');
      setStatus('idle');
    }
  }, [onTranscription]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && status === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, [status]);

  const handleMouseDown = () => {
    if (!disabled && status === 'idle') {
      startRecording();
    }
  };

  const handleMouseUp = () => {
    if (status === 'recording') {
      stopRecording();
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    e.preventDefault();
    handleMouseDown();
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    e.preventDefault();
    handleMouseUp();
  };

  return (
    <div className="relative">
      <button
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        disabled={disabled || status === 'processing'}
        className={clsx(
          'p-3 rounded-full transition-all duration-200',
          status === 'recording'
            ? 'bg-red-500 text-white voice-recording scale-110'
            : status === 'processing'
            ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 cursor-not-allowed'
            : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        title={
          status === 'recording'
            ? '松开发送'
            : status === 'processing'
            ? '处理中...'
            : '按住说话'
        }
      >
        {status === 'processing' ? (
          <Loader2 className="w-6 h-6 animate-spin" />
        ) : status === 'recording' ? (
          <MicOff className="w-6 h-6" />
        ) : (
          <Mic className="w-6 h-6" />
        )}
      </button>

      {/* Status text */}
      {status === 'recording' && (
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <span className="px-2 py-1 rounded bg-red-500 text-white text-xs">
            正在录音，松开发送
          </span>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <span className="px-2 py-1 rounded bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-xs">
            {error}
          </span>
        </div>
      )}
    </div>
  );
}

// Convert audio blob to WAV format
async function convertToWav(blob: Blob): Promise<Blob> {
  const audioContext = new AudioContext({ sampleRate: 16000 });
  const arrayBuffer = await blob.arrayBuffer();
  
  try {
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    const wavBuffer = audioBufferToWav(audioBuffer);
    return new Blob([wavBuffer], { type: 'audio/wav' });
  } finally {
    await audioContext.close();
  }
}

// Convert AudioBuffer to WAV format
function audioBufferToWav(buffer: AudioBuffer): ArrayBuffer {
  const numChannels = 1;
  const sampleRate = buffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;

  const data = buffer.getChannelData(0);
  const dataLength = data.length * (bitDepth / 8);
  const headerLength = 44;
  const totalLength = headerLength + dataLength;

  const arrayBuffer = new ArrayBuffer(totalLength);
  const view = new DataView(arrayBuffer);

  // WAV header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, totalLength - 8, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, format, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * (bitDepth / 8), true);
  view.setUint16(32, numChannels * (bitDepth / 8), true);
  view.setUint16(34, bitDepth, true);
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  // Audio data
  let offset = 44;
  for (let i = 0; i < data.length; i++) {
    const sample = Math.max(-1, Math.min(1, data[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }

  return arrayBuffer;
}

function writeString(view: DataView, offset: number, string: string): void {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}
