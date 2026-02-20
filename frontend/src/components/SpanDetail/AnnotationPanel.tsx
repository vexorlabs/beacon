import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useTraceStore } from "@/store/trace";
import type { Annotation } from "@/lib/types";

interface AnnotationPanelProps {
  spanId: string;
  annotations: Annotation[];
}

export default function AnnotationPanel({
  spanId,
  annotations,
}: AnnotationPanelProps) {
  const updateSpanAnnotations = useTraceStore(
    (s) => s.updateSpanAnnotations,
  );
  const [newText, setNewText] = useState("");

  const handleAdd = () => {
    if (!newText.trim()) return;
    const newAnnotation: Annotation = {
      id: crypto.randomUUID(),
      text: newText.trim(),
      created_at: Date.now() / 1000,
    };
    void updateSpanAnnotations(spanId, [...annotations, newAnnotation]);
    setNewText("");
  };

  const handleDelete = (id: string) => {
    void updateSpanAnnotations(
      spanId,
      annotations.filter((a) => a.id !== id),
    );
  };

  return (
    <div>
      <div className="border-b border-border my-4" />
      <h4 className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
        Annotations
      </h4>
      {annotations.map((a) => (
        <div
          key={a.id}
          className="group flex items-start gap-2 mb-2 text-[12px]"
        >
          <p className="flex-1 text-foreground bg-card border border-border rounded-md px-2 py-1.5">
            {a.text}
          </p>
          <button
            type="button"
            onClick={() => handleDelete(a.id)}
            className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive mt-1 transition-opacity"
          >
            <Trash2 size={12} />
          </button>
        </div>
      ))}
      <div className="flex gap-2">
        <textarea
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          placeholder="Add a note to this span..."
          rows={2}
          className="flex-1 bg-background border border-input rounded-md px-2 py-1.5 text-[12px] outline-none focus:ring-1 focus:ring-ring resize-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAdd();
          }}
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={!newText.trim()}
          className="self-end h-7 px-2 text-[11px] font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          Add
        </button>
      </div>
    </div>
  );
}
