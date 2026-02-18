interface TimelineHeaderProps {
  traceStartTime: number;
  traceEndTime: number;
  containerWidth: number;
}

/** Pick a nice tick interval based on the total duration. */
function pickTickInterval(totalSec: number): number {
  const candidates = [
    0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300,
  ];
  // Aim for ~5-10 ticks
  for (const c of candidates) {
    if (totalSec / c <= 12) return c;
  }
  return totalSec / 5;
}

function formatTick(sec: number): string {
  if (sec < 1) return `${Math.round(sec * 1000)}ms`;
  if (sec < 60) return `${sec % 1 === 0 ? sec : sec.toFixed(1)}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s === 0 ? `${m}m` : `${m}m${s}s`;
}

export default function TimelineHeader({
  traceStartTime,
  traceEndTime,
  containerWidth,
}: TimelineHeaderProps) {
  const totalSec = traceEndTime - traceStartTime;
  if (totalSec <= 0 || containerWidth <= 0) return null;

  const interval = pickTickInterval(totalSec);
  const pxPerSec = containerWidth / totalSec;

  const ticks: { offsetPx: number; label: string }[] = [];
  for (let t = 0; t <= totalSec + interval * 0.01; t += interval) {
    ticks.push({
      offsetPx: t * pxPerSec,
      label: formatTick(t),
    });
  }

  return (
    <div
      className="relative h-6 border-b border-border/60 bg-card/50 text-[10px] text-muted-foreground flex-none select-none overflow-hidden"
      style={{ width: containerWidth }}
    >
      {ticks.map((tick) => (
        <div
          key={tick.label}
          className="absolute top-0 h-full flex flex-col justify-end"
          style={{ left: tick.offsetPx }}
        >
          <div className="absolute top-0 bottom-0 w-px bg-border/40" />
          <span className="pl-1 pb-0.5 leading-none">{tick.label}</span>
        </div>
      ))}
    </div>
  );
}
