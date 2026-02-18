import { useMemo } from "react";
import type { Span } from "@/lib/types";

export const ROW_HEIGHT = 32;
export const BAR_HEIGHT = 22;
const MIN_BAR_WIDTH = 2;

export interface TimelineSpan {
  span: Span;
  row: number;
  depth: number;
  leftPx: number;
  widthPx: number;
  isOnCriticalPath: boolean;
  durationMs: number | null;
  costUsd: number | null;
}

export interface TimelineLayout {
  spans: TimelineSpan[];
  totalRows: number;
  totalDurationMs: number;
  traceStartTime: number;
  traceEndTime: number;
  criticalPathSpanIds: Set<string>;
  slowestSpans: TimelineSpan[];
}

function buildChildrenMap(spans: Span[]): Map<string | null, Span[]> {
  const map = new Map<string | null, Span[]>();
  for (const span of spans) {
    const key = span.parent_span_id;
    const children = map.get(key);
    if (children) {
      children.push(span);
    } else {
      map.set(key, [span]);
    }
  }
  // Sort children by start_time within each parent group
  for (const children of map.values()) {
    children.sort((a, b) => a.start_time - b.start_time);
  }
  return map;
}

function computeCriticalPath(
  spans: Span[],
  childrenMap: Map<string | null, Span[]>,
): Set<string> {
  if (spans.length === 0) return new Set();

  // Bottom-up: compute latest end_time in each span's subtree
  const subtreeEnd = new Map<string, number>();

  function getSubtreeEnd(spanId: string, ownEndTime: number): number {
    const cached = subtreeEnd.get(spanId);
    if (cached !== undefined) return cached;

    const children = childrenMap.get(spanId) ?? [];
    let maxEnd = ownEndTime;
    for (const child of children) {
      const childEnd = child.end_time ?? ownEndTime;
      maxEnd = Math.max(maxEnd, getSubtreeEnd(child.span_id, childEnd));
    }
    subtreeEnd.set(spanId, maxEnd);
    return maxEnd;
  }

  // Initialize from all spans
  for (const span of spans) {
    getSubtreeEnd(span.span_id, span.end_time ?? span.start_time);
  }

  // Top-down: walk from root with latest subtreeEnd
  const roots = childrenMap.get(null) ?? [];
  if (roots.length === 0) return new Set();

  const criticalSet = new Set<string>();
  let current: Span | undefined = roots.reduce((a, b) =>
    (subtreeEnd.get(a.span_id) ?? 0) >= (subtreeEnd.get(b.span_id) ?? 0)
      ? a
      : b,
  );

  while (current) {
    criticalSet.add(current.span_id);
    const children = childrenMap.get(current.span_id) ?? [];
    if (children.length === 0) break;
    current = children.reduce((a, b) =>
      (subtreeEnd.get(a.span_id) ?? 0) >= (subtreeEnd.get(b.span_id) ?? 0)
        ? a
        : b,
    );
  }

  return criticalSet;
}

function computeLayout(
  spans: Span[],
  containerWidth: number,
): TimelineLayout {
  if (spans.length === 0) {
    return {
      spans: [],
      totalRows: 0,
      totalDurationMs: 0,
      traceStartTime: 0,
      traceEndTime: 0,
      criticalPathSpanIds: new Set(),
      slowestSpans: [],
    };
  }

  const childrenMap = buildChildrenMap(spans);

  // Compute trace time bounds
  let traceStart = Infinity;
  let traceEnd = -Infinity;
  for (const span of spans) {
    traceStart = Math.min(traceStart, span.start_time);
    const end = span.end_time ?? span.start_time;
    traceEnd = Math.max(traceEnd, end);
  }

  const totalDurationSec = traceEnd - traceStart;
  const totalDurationMs = totalDurationSec * 1000;
  const pxPerSec =
    totalDurationSec > 0 ? containerWidth / totalDurationSec : containerWidth;

  // Critical path
  const criticalPathSpanIds = computeCriticalPath(spans, childrenMap);

  // Row assignment via greedy packing during DFS
  const rowEndTimes: number[] = [];
  const result: TimelineSpan[] = [];

  function walk(parentId: string | null, depth: number): void {
    const children = childrenMap.get(parentId) ?? [];
    for (const span of children) {
      const endTime = span.end_time ?? traceEnd;
      const durationMs =
        span.end_time !== null
          ? (span.end_time - span.start_time) * 1000
          : null;
      const costUsd =
        typeof span.attributes["llm.cost_usd"] === "number"
          ? (span.attributes["llm.cost_usd"] as number)
          : null;

      // Find first row where span fits
      let assignedRow = -1;
      for (let r = 0; r < rowEndTimes.length; r++) {
        if (rowEndTimes[r] <= span.start_time) {
          assignedRow = r;
          break;
        }
      }
      if (assignedRow === -1) {
        assignedRow = rowEndTimes.length;
        rowEndTimes.push(0);
      }
      rowEndTimes[assignedRow] = endTime;

      const leftPx = (span.start_time - traceStart) * pxPerSec;
      const rawWidth = (endTime - span.start_time) * pxPerSec;
      const widthPx = Math.max(MIN_BAR_WIDTH, rawWidth);

      result.push({
        span,
        row: assignedRow,
        depth,
        leftPx,
        widthPx,
        isOnCriticalPath: criticalPathSpanIds.has(span.span_id),
        durationMs,
        costUsd,
      });

      // Recurse into children
      walk(span.span_id, depth + 1);
    }
  }

  walk(null, 0);

  // Top 5 slowest spans
  const slowestSpans = [...result]
    .filter((ts) => ts.durationMs !== null)
    .sort((a, b) => (b.durationMs ?? 0) - (a.durationMs ?? 0))
    .slice(0, 5);

  return {
    spans: result,
    totalRows: rowEndTimes.length,
    totalDurationMs,
    traceStartTime: traceStart,
    traceEndTime: traceEnd,
    criticalPathSpanIds,
    slowestSpans,
  };
}

export function useTimelineLayout(
  spans: Span[] | undefined,
  containerWidth: number,
): TimelineLayout {
  return useMemo(
    () => computeLayout(spans ?? [], containerWidth),
    [spans, containerWidth],
  );
}
