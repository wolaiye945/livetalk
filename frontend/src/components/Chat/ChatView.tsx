import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useConversationStore } from '@/stores/conversationStore';
import { authService } from '@/services/authService';
import MessageBubble from './MessageBubble';
import VoiceRecorder from '@/components/Voice/VoiceRecorder';
import { Send, Loader2, Download, Tag } from 'lucide-react';
import type { Message, WSMessage } from '@/types';

export default function ChatView() {
  const { conversationId } = useParams();
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const {
    currentConversation,
    messages,
    selectConversation,
    addMessage,
    fetchConversations,
    summarizeConversation,
    clearCurrentConversation,
  } = useConversationStore();

  // Load conversation
  useEffect(() => {
    if (conversationId) {
      selectConversation(Number(conversationId));
    } else {
      clearCurrentConversation();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [conversationId, selectConversation, clearCurrentConversation]);

  // Setup WebSocket
  useEffect(() => {
    if (!conversationId) return;

    const token = authService.getToken();
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/chat/ws/${conversationId}?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data: WSMessage = JSON.parse(event.data);
      handleWSMessage(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [conversationId]);

  const handleWSMessage = useCallback((data: WSMessage) => {
    switch (data.type) {
      case 'user_message':
        addMessage(data.message);
        break;
      case 'assistant_chunk':
        setStreamingContent((prev) => prev + data.content);
        break;
      case 'assistant_complete':
        setIsStreaming(false);
        setStreamingContent('');
        addMessage(data.message);
        fetchConversations();
        break;
      case 'error':
        console.error('Chat error:', data.message);
        setIsStreaming(false);
        break;
    }
  }, [addMessage, fetchConversations]);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const sendMessage = useCallback(() => {
    if (!inputValue.trim() || !wsRef.current || isStreaming) return;

    const content = inputValue.trim();
    setInputValue('');
    setIsStreaming(true);
    setStreamingContent('');

    wsRef.current.send(JSON.stringify({ content }));
  }, [inputValue, isStreaming]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleVoiceMessage = useCallback((text: string) => {
    if (!wsRef.current || isStreaming) return;
    
    setIsStreaming(true);
    setStreamingContent('');
    wsRef.current.send(JSON.stringify({ content: text }));
  }, [isStreaming]);

  const handleSummarize = async () => {
    if (!currentConversation) return;
    try {
      await summarizeConversation(currentConversation.id);
    } catch (error) {
      console.error('Summarize failed:', error);
    }
  };

  const handleExport = async (format: 'json' | 'markdown') => {
    if (!currentConversation) return;
    
    try {
      const response = await fetch(
        `/api/conversations/${currentConversation.id}/export?format=${format}`,
        {
          headers: {
            Authorization: `Bearer ${authService.getToken()}`,
          },
        }
      );
      const data = await response.json();
      
      let content: string;
      let filename: string;
      let mimeType: string;
      
      if (format === 'markdown') {
        content = data.content;
        filename = data.filename;
        mimeType = 'text/markdown';
      } else {
        content = JSON.stringify(data, null, 2);
        filename = `${currentConversation.title}.json`;
        mimeType = 'application/json';
      }
      
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  // Empty state
  if (!conversationId) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/20 flex items-center justify-center mx-auto mb-4">
            <Send className="w-8 h-8 text-primary-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            开始对话
          </h2>
          <p className="text-gray-500 dark:text-gray-400">
            选择一个对话或创建新对话开始聊天
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      {currentConversation && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {currentConversation.title}
            </h2>
            {currentConversation.tags && currentConversation.tags.length > 0 && (
              <div className="flex gap-1 mt-1">
                {currentConversation.tags.map((tag, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs rounded-full bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSummarize}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              title="生成总结和标签"
            >
              <Tag className="w-5 h-5 text-gray-500" />
            </button>
            <div className="relative group">
              <button
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                title="导出对话"
              >
                <Download className="w-5 h-5 text-gray-500" />
              </button>
              <div className="absolute right-0 mt-1 hidden group-hover:block">
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1">
                  <button
                    onClick={() => handleExport('json')}
                    className="w-full px-4 py-2 text-sm text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    导出 JSON
                  </button>
                  <button
                    onClick={() => handleExport('markdown')}
                    className="w-full px-4 py-2 text-sm text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    导出 Markdown
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          
          {/* Streaming message */}
          {isStreaming && streamingContent && (
            <MessageBubble
              message={{
                id: -1,
                conversation_id: Number(conversationId),
                role: 'assistant',
                content: streamingContent,
                token_count: 0,
                created_at: new Date().toISOString(),
              }}
              isStreaming
            />
          )}
          
          {/* Loading indicator */}
          {isStreaming && !streamingContent && (
            <div className="flex items-center gap-2 text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">正在思考...</span>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-3">
            {/* Voice recorder */}
            <VoiceRecorder
              conversationId={Number(conversationId)}
              onTranscription={handleVoiceMessage}
              disabled={isStreaming}
            />

            {/* Text input */}
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息..."
                rows={1}
                className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white resize-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                style={{ minHeight: '48px', maxHeight: '200px' }}
              />
              <button
                onClick={sendMessage}
                disabled={!inputValue.trim() || isStreaming}
                className="absolute right-2 bottom-2 p-2 rounded-lg bg-primary-500 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary-600 transition"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
          
          <p className="text-xs text-gray-400 text-center mt-2">
            按 Enter 发送，Shift+Enter 换行
          </p>
        </div>
      </div>
    </div>
  );
}
