import { describe, it, expect, vi, beforeEach } from "vitest";
import { useTraceStore } from "@/store/trace";
import {
  makeTrace,
  makeTraceDetail,
  makeGraphData,
  makeSpan,
  resetFixtures,
} from "@/test/fixtures";

vi.mock("@/lib/api", () => ({
  getTraces: vi.fn(),
  getTrace: vi.fn(),
  getTraceGraph: vi.fn(),
  postReplay: vi.fn(),
  deleteTrace: vi.fn(),
}));

const api = vi.mocked(await import("@/lib/api"));

beforeEach(() => {
  resetFixtures();
  useTraceStore.setState({
    traces: [],
    isLoadingTraces: false,
    selectedTraceId: null,
    selectedTrace: null,
    isLoadingTrace: false,
    graphData: null,
    selectedSpanId: null,
    selectedSpan: null,
    timeTravelIndex: null,
    replayResult: null,
    isReplaying: false,
    replayError: null,
    backendError: null,
    traceFilter: { status: "all", tags: [] },
  });
});

describe("useTraceStore", () => {
  describe("loadTraces", () => {
    it("fetches traces and updates state", async () => {
      const traces = [makeTrace(), makeTrace()];
      api.getTraces.mockResolvedValueOnce({
        traces,
        total: 2,
        limit: 50,
        offset: 0,
      });

      await useTraceStore.getState().loadTraces();

      expect(api.getTraces).toHaveBeenCalledWith({ limit: 50 });
      expect(useTraceStore.getState().traces).toEqual(traces);
      expect(useTraceStore.getState().isLoadingTraces).toBe(false);
      expect(useTraceStore.getState().backendError).toBeNull();
    });

    it("sets backendError when fetch fails and no traces exist", async () => {
      api.getTraces.mockRejectedValueOnce(new Error("Network error"));

      await useTraceStore.getState().loadTraces();

      expect(useTraceStore.getState().backendError).toBe("Network error");
      expect(useTraceStore.getState().isLoadingTraces).toBe(false);
    });

    it("does not set backendError when fetch fails but traces exist", async () => {
      useTraceStore.setState({ traces: [makeTrace()] });
      api.getTraces.mockRejectedValueOnce(new Error("Network error"));

      await useTraceStore.getState().loadTraces();

      expect(useTraceStore.getState().backendError).toBeNull();
    });
  });

  describe("selectTrace", () => {
    it("fetches trace detail and graph data", async () => {
      const detail = makeTraceDetail();
      const graph = makeGraphData();
      api.getTrace.mockResolvedValueOnce(detail);
      api.getTraceGraph.mockResolvedValueOnce(graph);

      await useTraceStore.getState().selectTrace("trace-1");

      expect(useTraceStore.getState().selectedTraceId).toBe("trace-1");
      expect(useTraceStore.getState().selectedTrace).toEqual(detail);
      expect(useTraceStore.getState().graphData).toEqual(graph);
      expect(useTraceStore.getState().isLoadingTrace).toBe(false);
    });

    it("clears selected span when selecting a new trace", async () => {
      useTraceStore.setState({
        selectedSpanId: "old-span",
        selectedSpan: makeSpan(),
      });
      api.getTrace.mockResolvedValueOnce(makeTraceDetail());
      api.getTraceGraph.mockResolvedValueOnce(makeGraphData());

      await useTraceStore.getState().selectTrace("trace-new");

      expect(useTraceStore.getState().selectedSpanId).toBeNull();
      expect(useTraceStore.getState().selectedSpan).toBeNull();
    });
  });

  describe("selectSpan", () => {
    it("finds span from selectedTrace and sets it", () => {
      const span = makeSpan({ span_id: "target-span" });
      useTraceStore.setState({
        selectedTrace: makeTraceDetail({ spans: [span] }),
      });

      useTraceStore.getState().selectSpan("target-span");

      expect(useTraceStore.getState().selectedSpanId).toBe("target-span");
      expect(useTraceStore.getState().selectedSpan).toEqual(span);
    });

    it("sets selectedSpan to null if span not found", () => {
      useTraceStore.setState({
        selectedTrace: makeTraceDetail({ spans: [] }),
      });

      useTraceStore.getState().selectSpan("nonexistent");

      expect(useTraceStore.getState().selectedSpanId).toBe("nonexistent");
      expect(useTraceStore.getState().selectedSpan).toBeNull();
    });
  });

  describe("appendSpan", () => {
    it("increments span_count in matching trace", () => {
      const trace = makeTrace({ trace_id: "t1", span_count: 2 });
      useTraceStore.setState({ traces: [trace] });

      useTraceStore
        .getState()
        .appendSpan(makeSpan({ trace_id: "t1", span_id: "new-span" }));

      expect(useTraceStore.getState().traces[0].span_count).toBe(3);
    });

    it("adds span to selectedTrace when it matches", () => {
      const graph = makeGraphData(1);
      const detail = makeTraceDetail({ trace_id: "t1", spans: [] });
      useTraceStore.setState({
        traces: [makeTrace({ trace_id: "t1" })],
        selectedTraceId: "t1",
        selectedTrace: detail,
        graphData: graph,
      });

      const newSpan = makeSpan({
        trace_id: "t1",
        span_id: "appended",
        parent_span_id: graph.nodes[0].id,
      });
      useTraceStore.getState().appendSpan(newSpan);

      const state = useTraceStore.getState();
      expect(state.selectedTrace?.spans).toHaveLength(1);
      expect(state.graphData?.nodes).toHaveLength(2);
      expect(state.graphData?.edges).toHaveLength(1);
    });
  });

  describe("deleteTrace", () => {
    it("removes trace from list", async () => {
      const t1 = makeTrace({ trace_id: "t1" });
      const t2 = makeTrace({ trace_id: "t2" });
      useTraceStore.setState({ traces: [t1, t2] });
      api.deleteTrace.mockResolvedValueOnce({ deleted_count: 1 });

      await useTraceStore.getState().deleteTrace("t1");

      expect(useTraceStore.getState().traces).toHaveLength(1);
      expect(useTraceStore.getState().traces[0].trace_id).toBe("t2");
    });

    it("clears selection when deleting selected trace", async () => {
      useTraceStore.setState({
        traces: [makeTrace({ trace_id: "t1" })],
        selectedTraceId: "t1",
        selectedTrace: makeTraceDetail(),
        graphData: makeGraphData(),
        selectedSpanId: "s1",
        selectedSpan: makeSpan(),
      });
      api.deleteTrace.mockResolvedValueOnce({ deleted_count: 1 });

      await useTraceStore.getState().deleteTrace("t1");

      expect(useTraceStore.getState().selectedTraceId).toBeNull();
      expect(useTraceStore.getState().selectedTrace).toBeNull();
      expect(useTraceStore.getState().graphData).toBeNull();
    });
  });

  describe("setTraceFilter", () => {
    it("merges partial filter into existing filter", () => {
      useTraceStore.getState().setTraceFilter({ status: "error" });
      expect(useTraceStore.getState().traceFilter.status).toBe("error");
    });
  });
});
