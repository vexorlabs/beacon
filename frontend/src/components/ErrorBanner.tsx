import { X } from "lucide-react";
import { useTraceStore } from "@/store/trace";

export default function ErrorBanner() {
  const backendError = useTraceStore((s) => s.backendError);
  const clearBackendError = useTraceStore((s) => s.clearBackendError);

  if (!backendError) return null;

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-red-950/30 border-b border-red-900/40 text-xs text-red-400">
      <span>
        Backend unreachable at localhost:7474. Start the backend with{" "}
        <code className="font-mono">make dev</code>.
      </span>
      <button
        type="button"
        onClick={clearBackendError}
        className="ml-4 text-red-400 hover:text-red-300 flex-none"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  );
}
