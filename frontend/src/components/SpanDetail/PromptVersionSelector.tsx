import { useCallback, useEffect, useState } from "react";
import { History, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getPromptVersions, createPromptVersion } from "@/lib/api";
import type { PromptVersion } from "@/lib/types";

interface PromptVersionSelectorProps {
  spanId: string;
  currentPrompt: string;
  onRestore: (promptText: string) => void;
}

function formatRelativeTime(timestamp: number): string {
  const seconds = Math.floor(Date.now() / 1000 - timestamp);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function PromptVersionSelector({
  spanId,
  currentPrompt,
  onRestore,
}: PromptVersionSelectorProps) {
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  const fetchVersions = useCallback(async () => {
    try {
      const res = await getPromptVersions(spanId);
      setVersions(res.versions);
    } catch {
      // Silently ignore — versions are optional
    }
  }, [spanId]);

  useEffect(() => {
    void fetchVersions();
  }, [fetchVersions]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await createPromptVersion(spanId, currentPrompt);
      await fetchVersions();
    } catch {
      // Silently ignore
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => void handleSave()}
        disabled={isSaving}
        className="h-7 px-2 text-[11px]"
      >
        <Save size={12} className="mr-1" />
        {isSaving ? "Saving..." : "Save"}
      </Button>

      {versions.length > 0 && (
        <DropdownMenu onOpenChange={(open) => { if (open) void fetchVersions(); }}>
          <DropdownMenuTrigger asChild>
            <Button size="sm" variant="ghost" className="h-7 px-2 text-[11px]">
              <History size={12} className="mr-1" />
              History ({versions.length})
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-64">
            {versions.map((v) => (
              <DropdownMenuItem
                key={v.version_id}
                onClick={() => onRestore(v.prompt_text)}
                className="flex flex-col items-start gap-0.5 py-2"
              >
                <div className="flex items-center gap-2 w-full">
                  <span className="text-xs font-medium truncate">
                    {v.label ?? "Untitled"}
                  </span>
                  <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
                    {formatRelativeTime(v.created_at)}
                  </span>
                </div>
                <span className="text-[10px] text-muted-foreground truncate w-full">
                  {v.prompt_text.slice(0, 60)}
                  {v.prompt_text.length > 60 ? "..." : ""}
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
