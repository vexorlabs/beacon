import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDemoScenarios, runDemoAgent } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2, Play, Settings } from "lucide-react";
import type { DemoScenario } from "@/lib/types";

export default function DemoAgents() {
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningKey, setRunningKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getDemoScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([]))
      .finally(() => setLoading(false));
  }, []);

  const handleRun = async (key: string) => {
    setRunningKey(key);
    setError(null);
    try {
      const res = await runDemoAgent(key);
      navigate(`/traces/${res.trace_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start demo");
    } finally {
      setRunningKey(null);
    }
  };

  if (loading) {
    return null;
  }

  if (scenarios.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-sm font-medium text-foreground">
          Try a Demo Agent
        </h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Run a pre-built agent with real LLM calls. Watch the trace build live.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {scenarios.map((s) => (
          <div
            key={s.key}
            className="border border-border rounded-lg p-4 space-y-3 flex flex-col"
          >
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-[13px] font-medium text-foreground">
                  {s.name}
                </span>
                <Badge variant="secondary" className="text-[10px]">
                  {s.model}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {s.description}
              </p>
            </div>

            {s.api_key_configured ? (
              <Button
                size="sm"
                className="w-full"
                disabled={runningKey !== null}
                onClick={() => handleRun(s.key)}
              >
                {runningKey === s.key ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play size={14} />
                    Run Agent
                  </>
                )}
              </Button>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => navigate("/settings")}
              >
                <Settings size={14} />
                Configure {s.provider} key
              </Button>
            )}
          </div>
        ))}
      </div>

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}
