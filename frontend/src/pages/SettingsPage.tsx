import { useCallback, useEffect, useState } from "react";
import { KeyRound, Check, Trash2, Loader2, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getApiKeys,
  setApiKey,
  deleteApiKey,
  getStats,
  deleteAllTraces,
} from "@/lib/api";
import { useTraceStore } from "@/store/trace";
import type { ApiKeyStatus, StatsResponse } from "@/lib/types";

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
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [clearing, setClearing] = useState(false);
  const loadTraces = useTraceStore((s) => s.loadTraces);

  const loadKeys = useCallback(() => {
    getApiKeys()
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  const loadStats = useCallback(() => {
    getStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  useEffect(() => {
    loadKeys();
    loadStats();
  }, [loadKeys, loadStats]);

  const handleClearAll = async () => {
    setClearing(true);
    try {
      await deleteAllTraces();
      setConfirmClear(false);
      loadStats();
      void loadTraces();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to clear traces",
      );
    } finally {
      setClearing(false);
    }
  };

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

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Database size={16} className="text-muted-foreground" />
            <h2 className="text-sm font-medium text-foreground">
              Data Management
            </h2>
          </div>

          {stats && (
            <div className="grid grid-cols-2 gap-3">
              <div className="border border-border rounded-lg p-3">
                <div className="text-xs text-muted-foreground">Traces</div>
                <div className="text-lg font-semibold text-foreground mt-0.5">
                  {stats.total_traces}
                </div>
              </div>
              <div className="border border-border rounded-lg p-3">
                <div className="text-xs text-muted-foreground">Spans</div>
                <div className="text-lg font-semibold text-foreground mt-0.5">
                  {stats.total_spans.toLocaleString()}
                </div>
              </div>
              <div className="border border-border rounded-lg p-3">
                <div className="text-xs text-muted-foreground">
                  Database Size
                </div>
                <div className="text-lg font-semibold text-foreground mt-0.5">
                  {formatBytes(stats.database_size_bytes)}
                </div>
              </div>
              <div className="border border-border rounded-lg p-3">
                <div className="text-xs text-muted-foreground">
                  Oldest Trace
                </div>
                <div className="text-lg font-semibold text-foreground mt-0.5">
                  {stats.oldest_trace_timestamp
                    ? new Date(
                        stats.oldest_trace_timestamp * 1000,
                      ).toLocaleDateString()
                    : "—"}
                </div>
              </div>
            </div>
          )}

          <div className="border border-border rounded-lg p-4 space-y-3">
            <div>
              <span className="text-[13px] font-medium text-foreground">
                Clear All Traces
              </span>
              <p className="text-xs text-muted-foreground mt-0.5">
                Permanently delete all traces, spans, and replay data.
              </p>
            </div>
            {confirmClear ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => void handleClearAll()}
                  disabled={clearing}
                >
                  {clearing ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                  Confirm Delete All
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirmClear(false)}
                  disabled={clearing}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmClear(true)}
              >
                <Trash2 size={14} />
                Clear All Traces
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
