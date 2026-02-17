import { useState } from "react";
import {
  RotateCcw,
  ExternalLink,
  KeyRound,
  ChevronDown,
  ChevronUp,
  GitCompareArrows,
  MessageSquare,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import ModelSelector from "./ModelSelector";
import ChatPanel from "./ChatPanel";
import CompareView from "./CompareView";
import { usePlaygroundStore } from "@/store/playground";

interface Props {
  onViewInDebugger: () => void;
  onOpenSettings: () => void;
}

export default function Playground({ onViewInDebugger, onOpenSettings }: Props) {
  const [systemPromptOpen, setSystemPromptOpen] = useState(false);

  const selectedModel = usePlaygroundStore((s) => s.selectedModel);
  const setSelectedModel = usePlaygroundStore((s) => s.setSelectedModel);
  const systemPrompt = usePlaygroundStore((s) => s.systemPrompt);
  const setSystemPrompt = usePlaygroundStore((s) => s.setSystemPrompt);
  const compareMode = usePlaygroundStore((s) => s.compareMode);
  const setCompareMode = usePlaygroundStore((s) => s.setCompareMode);
  const clearConversation = usePlaygroundStore((s) => s.clearConversation);
  const traceId = usePlaygroundStore((s) => s.traceId);
  const compareTraceId = usePlaygroundStore((s) => s.compareTraceId);
  const error = usePlaygroundStore((s) => s.error);
  const clearError = usePlaygroundStore((s) => s.clearError);
  const isSending = usePlaygroundStore((s) => s.isSending);
  const isComparing = usePlaygroundStore((s) => s.isComparing);

  const activeTraceId = compareMode ? compareTraceId : traceId;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border flex-none">
        {/* Mode toggle */}
        <div className="flex items-center border border-border rounded-md overflow-hidden">
          <button
            type="button"
            onClick={() => setCompareMode(false)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${
              !compareMode
                ? "bg-secondary text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <MessageSquare size={12} />
            Chat
          </button>
          <button
            type="button"
            onClick={() => setCompareMode(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${
              compareMode
                ? "bg-secondary text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <GitCompareArrows size={12} />
            Compare
          </button>
        </div>

        {!compareMode && (
          <ModelSelector
            value={selectedModel}
            onChange={setSelectedModel}
            disabled={isSending}
          />
        )}

        <button
          type="button"
          onClick={() => setSystemPromptOpen(!systemPromptOpen)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          System
          {systemPromptOpen ? (
            <ChevronUp size={12} />
          ) : (
            <ChevronDown size={12} />
          )}
        </button>

        <div className="flex-1" />

        {activeTraceId && (
          <Button variant="ghost" size="xs" onClick={onViewInDebugger}>
            <ExternalLink size={12} />
            View in Debugger
          </Button>
        )}

        <Button
          variant="ghost"
          size="xs"
          onClick={clearConversation}
          disabled={isSending || isComparing}
        >
          <RotateCcw size={12} />
          Clear
        </Button>

        <Button variant="ghost" size="xs" onClick={onOpenSettings}>
          <KeyRound size={12} />
          API Keys
        </Button>
      </div>

      {/* System prompt */}
      {systemPromptOpen && (
        <div className="border-b border-border px-4 py-3 flex-none">
          <textarea
            className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Optional system prompt..."
            rows={3}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center justify-between px-4 py-2 bg-red-950/30 border-b border-red-900/40 text-xs text-red-400 flex-none">
          <span>{error}</span>
          <button
            type="button"
            onClick={clearError}
            className="ml-4 text-red-400 hover:text-red-300"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 min-h-0">
        {compareMode ? <CompareView /> : <ChatPanel />}
      </div>
    </div>
  );
}
