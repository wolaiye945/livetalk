import api from './api';
import type { Conversation, ConversationGroup, Message, ChatResponse, ExportResponse } from '@/types';

export const conversationService = {
  // Conversations
  async getConversations(params?: {
    group_id?: number;
    search?: string;
    is_archived?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<Conversation[]> {
    const response = await api.get<Conversation[]>('/conversations', { params });
    return response.data;
  },

  async createConversation(data: { title?: string; group_id?: number }): Promise<Conversation> {
    const response = await api.post<Conversation>('/conversations', data);
    return response.data;
  },

  async getConversation(id: number): Promise<Conversation> {
    const response = await api.get<Conversation>(`/conversations/${id}`);
    return response.data;
  },

  async updateConversation(
    id: number,
    data: { title?: string; group_id?: number; tags?: string[]; is_archived?: boolean }
  ): Promise<Conversation> {
    const response = await api.put<Conversation>(`/conversations/${id}`, data);
    return response.data;
  },

  async deleteConversation(id: number): Promise<void> {
    await api.delete(`/conversations/${id}`);
  },

  async batchDeleteConversations(ids: number[]): Promise<void> {
    await api.delete('/conversations/batch', { data: { ids } });
  },

  async summarizeConversation(id: number): Promise<{ summary: string; tags: string[] }> {
    const response = await api.post<{ summary: string; tags: string[] }>(
      `/conversations/${id}/summarize`
    );
    return response.data;
  },

  async exportConversation(id: number, format: 'json' | 'markdown'): Promise<ExportResponse> {
    const response = await api.get<ExportResponse>(`/conversations/${id}/export`, {
      params: { format },
    });
    return response.data;
  },

  // Groups
  async getGroups(): Promise<ConversationGroup[]> {
    const response = await api.get<ConversationGroup[]>('/groups');
    return response.data;
  },

  async createGroup(name: string): Promise<ConversationGroup> {
    const response = await api.post<ConversationGroup>('/groups', { name });
    return response.data;
  },

  async updateGroup(id: number, data: { name?: string; order_index?: number }): Promise<ConversationGroup> {
    const response = await api.put<ConversationGroup>(`/groups/${id}`, data);
    return response.data;
  },

  async deleteGroup(id: number): Promise<void> {
    await api.delete(`/groups/${id}`);
  },

  // Messages
  async getMessages(conversationId: number): Promise<Message[]> {
    const response = await api.get<Message[]>(`/chat/${conversationId}/messages`);
    return response.data;
  },

  async sendMessage(conversationId: number, content: string): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>(`/chat/${conversationId}/messages`, {
      content,
    });
    return response.data;
  },
};
