import { useCallback, useEffect, useRef, useState } from "react";
import { KeyRound, Check, Trash2, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getApiKeys, setApiKey, deleteApiKey } from "@/lib/api";
import type { ApiKeyStatus } from "@/lib/types";

interface Props {
  open: boolean;
  onClose: () => void;
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
};

export default function ApiKeyDialog({ open, onClose }: Props) {
  const [providers, setProviders] = useState<ApiKeyStatus[]>([]);
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDivElement>(null);

  // Document-level Escape key handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      getApiKeys()
        .then(setProviders)
        .catch(() => setProviders([]));
      setEditingProvider(null);
      setKeyInput("");
      setError(null);
      document.addEventListener("keydown", handleKeyDown);
      // Focus trap: focus the dialog on open
      requestAnimationFrame(() => dialogRef.current?.focus());
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [open, handleKeyDown]);

  if (!open) return null;

  const handleSave = async (provider: string) => {
    if (!keyInput.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await setApiKey(provider, keyInput.trim());
      const updated = await getApiKeys();
      setProviders(updated);
      setEditingProvider(null);
      setKeyInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save key");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (provider: string) => {
    setSaving(true);
    try {
      await deleteApiKey(provider);
      const updated = await getApiKeys();
      setProviders(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete key");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="API Keys"
        tabIndex={-1}
        className="relative bg-card border border-border rounded-lg shadow-lg w-full max-w-md p-6 focus:outline-none"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <KeyRound size={18} className="text-muted-foreground" />
            <h2 className="text-lg font-semibold">API Keys</h2>
          </div>
          <Button variant="ghost" size="icon-xs" onClick={onClose}>
            <X size={14} />
          </Button>
        </div>

        <p className="text-xs text-muted-foreground mb-4">
          Keys are stored locally at ~/.beacon/config.json and never leave your
          machine.
        </p>

        {error && (
          <div className="text-xs text-red-400 bg-red-950/30 border border-red-900/40 rounded px-3 py-2 mb-3">
            {error}
          </div>
        )}

        <div className="space-y-3">
          {providers.map((p) => (
            <div
              key={p.provider}
              className="border border-border rounded-md p-3"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium">
                  {PROVIDER_LABELS[p.provider] ?? p.provider}
                </span>
                {p.configured ? (
                  <Badge
                    variant="secondary"
                    className="text-green-600 dark:text-green-400"
                  >
                    <Check size={10} className="mr-0.5" />
                    Configured
                  </Badge>
                ) : (
                  <Badge variant="outline">Not set</Badge>
                )}
              </div>

              {p.configured && editingProvider !== p.provider && (
                <div className="flex items-center justify-between mt-2">
                  <code className="text-xs text-muted-foreground font-mono">
                    {p.masked_key}
                  </code>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => {
                        setEditingProvider(p.provider);
                        setKeyInput("");
                      }}
                    >
                      Update
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      className="text-destructive"
                      onClick={() => handleDelete(p.provider)}
                      disabled={saving}
                    >
                      <Trash2 size={12} />
                    </Button>
                  </div>
                </div>
              )}

              {(editingProvider === p.provider || !p.configured) &&
                editingProvider !== null &&
                editingProvider === p.provider && (
                  <div className="flex gap-2 mt-2">
                    <input
                      type="password"
                      className="flex-1 bg-background border border-input rounded-md px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                      placeholder={
                        p.provider === "openai"
                          ? "sk-..."
                          : "sk-ant-..."
                      }
                      value={keyInput}
                      onChange={(e) => setKeyInput(e.target.value)}
                      onKeyDown={(e) =>
                        e.key === "Enter" && handleSave(p.provider)
                      }
                      autoFocus
                    />
                    <Button
                      size="sm"
                      onClick={() => handleSave(p.provider)}
                      disabled={saving || !keyInput.trim()}
                    >
                      {saving ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        "Save"
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setEditingProvider(null);
                        setKeyInput("");
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                )}

              {!p.configured && editingProvider !== p.provider && (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 w-full"
                  onClick={() => {
                    setEditingProvider(p.provider);
                    setKeyInput("");
                  }}
                >
                  Add API Key
                </Button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
