import TraceList from "@/components/TraceList";
import TraceGraph from "@/components/TraceGraph";
import SpanDetail from "@/components/SpanDetail";
import TimeTravel from "@/components/TimeTravel";
import CostSummaryBar from "@/components/CostSummaryBar";
import { useResizablePanels } from "@/lib/useResizablePanels";

export default function TracesPage() {
  const { leftWidth, rightWidth, leftHandleProps, rightHandleProps } =
    useResizablePanels(280, 380);

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden">
      <div
        style={{ width: leftWidth, flexShrink: 0 }}
        className="border-r border-border flex flex-col"
      >
        <TraceList />
      </div>
      <div
        {...leftHandleProps}
        className="w-1 cursor-col-resize hover:bg-primary/30 active:bg-primary/50 transition-colors flex-none"
        role="separator"
        aria-label="Resize trace list"
      />
      <div className="flex-1 min-w-0 flex flex-col">
        <CostSummaryBar />
        <div className="flex-1 min-h-0">
          <TraceGraph />
        </div>
        <TimeTravel />
      </div>
      <div
        {...rightHandleProps}
        className="w-1 cursor-col-resize hover:bg-primary/30 active:bg-primary/50 transition-colors flex-none"
        role="separator"
        aria-label="Resize span detail"
      />
      <div
        style={{ width: rightWidth, flexShrink: 0 }}
        className="border-l border-border"
      >
        <SpanDetail />
      </div>
    </div>
  );
}
