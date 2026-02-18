import { useRef, useEffect, useState, useCallback } from "react";
import { Send, Loader2, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import MessageBubble from "./MessageBubble";
import { usePlaygroundStore } from "@/store/playground";

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const messages = usePlaygroundStore((s) => s.messages);
  const isSending = usePlaygroundStore((s) => s.isSending);
  const sendMessage = usePlaygroundStore((s) => s.sendMessage);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isSending) return;
    setInput("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    sendMessage(trimmed);
  };

  const handleTextareaChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value);
      e.target.style.height = "auto";
      e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
    },
    [],
  );

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-3 max-w-xs">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mx-auto">
                <MessageSquare size={18} className="text-primary" />
              </div>
              <div>
                <p className="text-[13px] text-foreground font-medium">
                  Start a conversation
                </p>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  Every message creates a trace visible in the Debugger.
                </p>
              </div>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            role={msg.role}
            content={msg.content}
            metrics={msg.metrics}
          />
        ))}
        {isSending && (
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Loader2 size={14} className="animate-spin" />
            Waiting for response...
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-border p-3">
        <div className="flex items-end gap-2 bg-card border-[0.5px] border-border rounded-lg p-2 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
          <textarea
            ref={textareaRef}
            className="flex-1 bg-transparent resize-none text-[13px] placeholder:text-muted-foreground/60 focus:outline-none min-h-[36px] max-h-[120px] py-1.5 px-2 leading-relaxed"
            aria-label="Chat message"
            placeholder="Send a message..."
            rows={1}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isSending}
          />
          <Button
            size="icon-sm"
            onClick={handleSend}
            disabled={isSending || !input.trim()}
            className="flex-none rounded-md"
          >
            {isSending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
          </Button>
        </div>
        <div className="flex items-center gap-2 mt-1.5 px-1">
          <span className="text-[11px] text-muted-foreground/50">
            <kbd className="border-[0.5px] border-border rounded px-1 py-0.5 text-[10px] font-mono">
              Enter
            </kbd>{" "}
            to send
          </span>
        </div>
      </div>
    </div>
  );
}
