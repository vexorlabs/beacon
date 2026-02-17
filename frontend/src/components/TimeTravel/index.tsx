import { useCallback, useEffect } from "react";
import { useTraceStore } from "@/store/trace";
import { Slider } from "@/components/ui/slider";

export default function TimeTravel() {
  const graphData = useTraceStore((s) => s.graphData);
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const timeTravelIndex = useTraceStore((s) => s.timeTravelIndex);
  const setTimeTravelIndex = useTraceStore((s) => s.setTimeTravelIndex);

  const totalSteps = graphData?.nodes.length ?? 0;
  const currentValue = timeTravelIndex ?? totalSteps;

  const handleSliderChange = useCallback(
    (values: number[]) => {
      const value = values[0];
      setTimeTravelIndex(value >= totalSteps ? null : value);
    },
    [totalSteps, setTimeTravelIndex],
  );

  useEffect(() => {
    if (!selectedTraceId || totalSteps === 0) return;

    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      // Skip when Monaco Editor is focused
      if ((e.target as HTMLElement)?.closest(".monaco-editor")) return;

      if (e.key === "ArrowRight") {
        e.preventDefault();
        const current = timeTravelIndex ?? totalSteps;
        if (current < totalSteps) {
          setTimeTravelIndex(current + 1 >= totalSteps ? null : current + 1);
        }
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        const current = timeTravelIndex ?? totalSteps;
        if (current > 0) {
          setTimeTravelIndex(current - 1);
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [selectedTraceId, totalSteps, timeTravelIndex, setTimeTravelIndex]);

  if (!selectedTraceId || !graphData || totalSteps === 0) return null;

  return (
    <div className="flex items-center gap-3 h-12 px-4 border-t border-border">
      <Slider
        min={0}
        max={totalSteps}
        step={1}
        value={[currentValue]}
        onValueChange={handleSliderChange}
        className="flex-1"
      />
      <span className="text-xs text-muted-foreground whitespace-nowrap min-w-[80px] text-right">
        {timeTravelIndex !== null
          ? `Step ${timeTravelIndex + 1} / ${totalSteps}`
          : "All steps"}
      </span>
    </div>
  );
}
