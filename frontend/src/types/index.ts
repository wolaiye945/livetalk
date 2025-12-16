// User types
export interface User {
  id: number;
  username: string;
  role: 'user' | 'admin';
  created_at: string;
  updated_at: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterCredentials {
  username: string;
  password: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

// Conversation types
export interface ConversationGroup {
  id: number;
  name: string;
  order_index: number;
  created_at: string;
}

export interface Conversation {
  id: number;
  user_id: number;
  group_id: number | null;
  title: string;
  tags: string[];
  summary: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  audio_path?: string;
  token_count: number;
  created_at: string;
}

// WebSocket message types
export interface WSUserMessage {
  type: 'user_message';
  message: Message;
}

export interface WSAssistantChunk {
  type: 'assistant_chunk';
  content: string;
}

export interface WSAssistantComplete {
  type: 'assistant_complete';
  message: Message;
}

export interface WSStatus {
  type: 'status';
  status: 'transcribing' | 'thinking' | 'synthesizing';
}

export interface WSTranscription {
  type: 'transcription';
  text: string;
}

export interface WSAudio {
  type: 'assistant_audio';
  audio: string;
  format: string;
}

export interface WSError {
  type: 'error';
  message: string;
}

export type WSMessage = 
  | WSUserMessage 
  | WSAssistantChunk 
  | WSAssistantComplete 
  | WSStatus 
  | WSTranscription 
  | WSAudio 
  | WSError;

// API response types
export interface ChatResponse {
  message: Message;
  assistant_message: Message;
}

export interface ExportResponse {
  content?: string;
  filename?: string;
  id?: number;
  title?: string;
  tags?: string[];
  summary?: string;
  created_at?: string;
  messages?: Message[];
}
