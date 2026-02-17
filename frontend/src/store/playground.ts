import { create } from "zustand";
import { playgroundChat, playgroundCompare } from "@/lib/api";
import type {
  CompareResultItem,
  PlaygroundChatMetrics,
  PlaygroundMessage,
} from "@/lib/types";

export interface ChatMessage extends PlaygroundMessage {
  metrics?: PlaygroundChatMetrics;
}

interface PlaygroundStore {
  // Chat state
  messages: ChatMessage[];
  conversationId: string | null;
  traceId: string | null;
  selectedModel: string;
  systemPrompt: string;
  isSending: boolean;
  error: string | null;

  // Compare state
  compareMode: boolean;
  compareModels: string[];
  compareResults: CompareResultItem[] | null;
  compareTraceId: string | null;
  isComparing: boolean;

  // Actions
  sendMessage: (content: string) => Promise<void>;
  runComparison: (content: string) => Promise<void>;
  setSelectedModel: (model: string) => void;
  setSystemPrompt: (prompt: string) => void;
  setCompareMode: (enabled: boolean) => void;
  toggleCompareModel: (model: string) => void;
  clearConversation: () => void;
  clearError: () => void;
}

export const usePlaygroundStore = create<PlaygroundStore>((set, get) => ({
  messages: [],
  conversationId: null,
  traceId: null,
  selectedModel: "claude-sonnet-4-6",
  systemPrompt: "",
  isSending: false,
  error: null,

  compareMode: false,
  compareModels: ["gpt-4.1", "claude-sonnet-4-6"],
  compareResults: null,
  compareTraceId: null,
  isComparing: false,

  sendMessage: async (content: string) => {
    const { selectedModel, systemPrompt, messages, conversationId } = get();

    const userMessage: ChatMessage = { role: "user", content };
    const allMessages: PlaygroundMessage[] = [
      ...messages.map((m) => ({ role: m.role, content: m.content })),
      { role: "user" as const, content },
    ];

    set({
      messages: [...messages, userMessage],
      isSending: true,
      error: null,
    });

    try {
      const res = await playgroundChat({
        conversation_id: conversationId,
        model: selectedModel,
        system_prompt: systemPrompt || undefined,
        messages: allMessages,
      });

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: res.message.content,
        metrics: res.metrics,
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        conversationId: res.conversation_id,
        traceId: res.trace_id,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to send";
      set({ error: message });
    } finally {
      set({ isSending: false });
    }
  },

  runComparison: async (content: string) => {
    const { compareModels, systemPrompt } = get();

    set({
      isComparing: true,
      compareResults: null,
      compareTraceId: null,
      error: null,
    });

    try {
      const res = await playgroundCompare({
        messages: [{ role: "user", content }],
        system_prompt: systemPrompt || undefined,
        models: compareModels,
      });

      set({
        compareResults: res.results,
        compareTraceId: res.trace_id,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Comparison failed";
      set({ error: message });
    } finally {
      set({ isComparing: false });
    }
  },

  setSelectedModel: (model: string) => set({ selectedModel: model }),

  setSystemPrompt: (prompt: string) => set({ systemPrompt: prompt }),

  setCompareMode: (enabled: boolean) =>
    set({ compareMode: enabled, compareResults: null, compareTraceId: null }),

  toggleCompareModel: (model: string) =>
    set((state) => {
      const models = state.compareModels.includes(model)
        ? state.compareModels.filter((m) => m !== model)
        : [...state.compareModels, model];
      return { compareModels: models };
    }),

  clearConversation: () =>
    set({
      messages: [],
      conversationId: null,
      traceId: null,
      compareResults: null,
      compareTraceId: null,
      error: null,
    }),

  clearError: () => set({ error: null }),
}));
