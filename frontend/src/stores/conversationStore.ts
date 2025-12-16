import { create } from 'zustand';
import { conversationService } from '@/services/conversationService';
import type { Conversation, ConversationGroup, Message } from '@/types';

interface ConversationState {
  conversations: Conversation[];
  groups: ConversationGroup[];
  currentConversation: Conversation | null;
  messages: Message[];
  isLoading: boolean;
  searchQuery: string;
  selectedGroupId: number | null;

  // Conversations
  fetchConversations: () => Promise<void>;
  createConversation: (title?: string, groupId?: number) => Promise<Conversation>;
  selectConversation: (id: number) => Promise<void>;
  updateConversation: (id: number, data: Partial<Conversation>) => Promise<void>;
  deleteConversation: (id: number) => Promise<void>;
  summarizeConversation: (id: number) => Promise<void>;

  // Groups
  fetchGroups: () => Promise<void>;
  createGroup: (name: string) => Promise<void>;
  updateGroup: (id: number, name: string) => Promise<void>;
  deleteGroup: (id: number) => Promise<void>;
  setSelectedGroupId: (id: number | null) => void;

  // Messages
  fetchMessages: (conversationId: number) => Promise<void>;
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;

  // Search
  setSearchQuery: (query: string) => void;
  searchConversations: () => Promise<void>;

  // Clear
  clearCurrentConversation: () => void;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  groups: [],
  currentConversation: null,
  messages: [],
  isLoading: false,
  searchQuery: '',
  selectedGroupId: null,

  fetchConversations: async () => {
    set({ isLoading: true });
    try {
      const { searchQuery, selectedGroupId } = get();
      const conversations = await conversationService.getConversations({
        search: searchQuery || undefined,
        group_id: selectedGroupId ?? undefined,
        is_archived: false,
      });
      set({ conversations, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  createConversation: async (title?: string, groupId?: number) => {
    const conversation = await conversationService.createConversation({
      title: title || '新对话',
      group_id: groupId,
    });
    set((state) => ({
      conversations: [conversation, ...state.conversations],
    }));
    return conversation;
  },

  selectConversation: async (id: number) => {
    set({ isLoading: true });
    try {
      const [conversation, messages] = await Promise.all([
        conversationService.getConversation(id),
        conversationService.getMessages(id),
      ]);
      set({ currentConversation: conversation, messages, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  updateConversation: async (id: number, data: Partial<Conversation>) => {
    const updated = await conversationService.updateConversation(id, data);
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, ...updated } : c
      ),
      currentConversation:
        state.currentConversation?.id === id
          ? { ...state.currentConversation, ...updated }
          : state.currentConversation,
    }));
  },

  deleteConversation: async (id: number) => {
    await conversationService.deleteConversation(id);
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      currentConversation:
        state.currentConversation?.id === id ? null : state.currentConversation,
      messages: state.currentConversation?.id === id ? [] : state.messages,
    }));
  },

  summarizeConversation: async (id: number) => {
    const { summary, tags } = await conversationService.summarizeConversation(id);
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, summary, tags } : c
      ),
      currentConversation:
        state.currentConversation?.id === id
          ? { ...state.currentConversation, summary, tags }
          : state.currentConversation,
    }));
  },

  fetchGroups: async () => {
    const groups = await conversationService.getGroups();
    set({ groups });
  },

  createGroup: async (name: string) => {
    const group = await conversationService.createGroup(name);
    set((state) => ({ groups: [...state.groups, group] }));
  },

  updateGroup: async (id: number, name: string) => {
    const updated = await conversationService.updateGroup(id, { name });
    set((state) => ({
      groups: state.groups.map((g) => (g.id === id ? updated : g)),
    }));
  },

  deleteGroup: async (id: number) => {
    await conversationService.deleteGroup(id);
    set((state) => ({
      groups: state.groups.filter((g) => g.id !== id),
      selectedGroupId: state.selectedGroupId === id ? null : state.selectedGroupId,
    }));
  },

  setSelectedGroupId: (id: number | null) => {
    set({ selectedGroupId: id });
    get().fetchConversations();
  },

  fetchMessages: async (conversationId: number) => {
    const messages = await conversationService.getMessages(conversationId);
    set({ messages });
  },

  addMessage: (message: Message) => {
    set((state) => ({ messages: [...state.messages, message] }));
  },

  updateLastMessage: (content: string) => {
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        if (lastMessage.role === 'assistant') {
          messages[messages.length - 1] = { ...lastMessage, content };
        }
      }
      return { messages };
    });
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query });
  },

  searchConversations: async () => {
    await get().fetchConversations();
  },

  clearCurrentConversation: () => {
    set({ currentConversation: null, messages: [] });
  },
}));
