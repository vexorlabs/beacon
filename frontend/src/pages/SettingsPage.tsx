import { useCallback, useEffect, useState } from "react";
import { KeyRound, Check, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getApiKeys, setApiKey, deleteApiKey } from "@/lib/api";
import type { ApiKeyStatus } from "@/lib/types";

const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
};

export default function SettingsPage() {
  const [providers, setProviders] = useState<ApiKeyStatus[]>([]);
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadKeys = useCallback(() => {
    getApiKeys()
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

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
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-lg space-y-8">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Settings</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage API keys and configuration.
          </p>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <KeyRound size={16} className="text-muted-foreground" />
            <h2 className="text-sm font-medium text-foreground">API Keys</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            Keys are stored locally at ~/.beacon/config.json and never leave
            your machine.
          </p>

          {error && (
            <div className="text-xs text-red-400 bg-red-950/30 border border-red-900/40 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          <div className="space-y-3">
            {providers.map((p) => (
              <div
                key={p.provider}
                className="border border-border rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[13px] font-medium text-foreground">
                    {PROVIDER_LABELS[p.provider] ?? p.provider}
                  </span>
                  {p.configured ? (
                    <Badge
                      variant="secondary"
                      className="text-emerald-400"
                    >
                      <Check size={10} className="mr-0.5" />
                      Configured
                    </Badge>
                  ) : (
                    <Badge variant="outline">Not set</Badge>
                  )}
                </div>

                {p.configured && editingProvider !== p.provider && (
                  <div className="flex items-center justify-between mt-2 min-w-0">
                    <code className="text-xs text-muted-foreground font-mono truncate min-w-0">
                      {p.masked_key}
                    </code>
                    <div className="flex gap-1 flex-shrink-0">
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

                {editingProvider === p.provider && (
                  <div className="flex gap-2 mt-2">
                    <input
                      type="password"
                      className="flex-1 min-w-0 bg-background border border-input rounded-md px-3 py-1.5 text-[13px] font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                      placeholder={
                        p.provider === "openai" ? "sk-..." : "sk-ant-..."
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
    </div>
  );
}
