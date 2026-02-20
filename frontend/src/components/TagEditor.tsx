import { useState } from "react";
import { Plus, X } from "lucide-react";
import { useTraceStore } from "@/store/trace";

interface TagEditorProps {
  traceId: string;
  tags: Record<string, string>;
}

export default function TagEditor({ traceId, tags }: TagEditorProps) {
  const updateTraceTags = useTraceStore((s) => s.updateTraceTags);
  const [isAdding, setIsAdding] = useState(false);
  const [inputValue, setInputValue] = useState("");

  const handleAdd = () => {
    const [key, ...rest] = inputValue.split(":");
    const value = rest.join(":").trim();
    if (key.trim()) {
      const newTags = { ...tags, [key.trim()]: value || "" };
      void updateTraceTags(traceId, newTags);
      setInputValue("");
      setIsAdding(false);
    }
  };

  const handleRemove = (key: string) => {
    const newTags = { ...tags };
    delete newTags[key];
    void updateTraceTags(traceId, newTags);
  };

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {Object.entries(tags).map(([key, value]) => (
        <span
          key={key}
          className="inline-flex items-center gap-0.5 rounded-full bg-primary/10 border border-primary/20 px-1.5 py-0 text-[11px] text-primary"
        >
          {key}
          {value ? `: ${value}` : ""}
          <button
            type="button"
            onClick={() => handleRemove(key)}
            className="ml-0.5 hover:text-destructive transition-colors"
          >
            <X size={10} />
          </button>
        </span>
      ))}
      {isAdding ? (
        <input
          autoFocus
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAdd();
            if (e.key === "Escape") setIsAdding(false);
          }}
          onBlur={() => {
            if (!inputValue) setIsAdding(false);
          }}
          placeholder="key:value"
          className="h-5 w-24 bg-background border border-input rounded-full px-2 text-[11px] outline-none focus:ring-1 focus:ring-ring"
        />
      ) : (
        <button
          type="button"
          onClick={() => setIsAdding(true)}
          className="inline-flex items-center rounded-full border border-dashed border-muted-foreground/30 px-1.5 py-0 text-[11px] text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors"
        >
          <Plus size={10} className="mr-0.5" /> tag
        </button>
      )}
    </div>
  );
}
