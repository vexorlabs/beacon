import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useTraceStore } from "@/store/trace";
import { makeTrace, resetFixtures } from "@/test/fixtures";

// Mock SearchBar to avoid deep dependency tree
vi.mock("@/components/TraceList/SearchBar", () => ({
  default: () => <div data-testid="search-bar" />,
}));

// Mock TraceListItem to simplify rendering
vi.mock("@/components/TraceList/TraceListItem", () => ({
  default: ({
    trace,
  }: {
    trace: { trace_id: string; name: string };
  }) => <div data-testid={`trace-${trace.trace_id}`}>{trace.name}</div>,
}));

// Mock the API — default returns empty, tests can override
vi.mock("@/lib/api", () => ({
  getTraces: vi.fn(),
  getTrace: vi.fn(),
  getTraceGraph: vi.fn(),
  postReplay: vi.fn(),
  deleteTrace: vi.fn(),
  importTrace: vi.fn(),
}));

const api = vi.mocked(await import("@/lib/api"));

// Import after mocks
const { default: TraceList } = await import(
  "@/components/TraceList/index"
);

function renderTraceList() {
  return render(
    <MemoryRouter>
      <TraceList />
    </MemoryRouter>,
  );
}

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
    traceFilter: { status: "all" },
  });
  // Default: loadTraces returns empty
  api.getTraces.mockResolvedValue({
    traces: [],
    total: 0,
    limit: 50,
    offset: 0,
  });
});

describe("TraceList", () => {
  it("shows empty message when no traces exist", async () => {
    renderTraceList();

    // Wait for loadTraces to finish (useEffect fires on mount)
    await waitFor(() => {
      expect(screen.getByText(/no traces yet/i)).toBeInTheDocument();
    });
  });

  it("renders trace items when API returns traces", async () => {
    const traces = [
      makeTrace({ trace_id: "t1", name: "Agent Run 1" }),
      makeTrace({ trace_id: "t2", name: "Agent Run 2" }),
    ];
    api.getTraces.mockResolvedValueOnce({
      traces,
      total: 2,
      limit: 50,
      offset: 0,
    });

    renderTraceList();

    await waitFor(() => {
      expect(screen.getByTestId("trace-t1")).toBeInTheDocument();
      expect(screen.getByTestId("trace-t2")).toBeInTheDocument();
      expect(screen.getByText("Agent Run 1")).toBeInTheDocument();
      expect(screen.getByText("Agent Run 2")).toBeInTheDocument();
    });
  });

  it("shows filtered count in badge", async () => {
    const traces = [
      makeTrace({ trace_id: "t1" }),
      makeTrace({ trace_id: "t2" }),
    ];
    api.getTraces.mockResolvedValueOnce({
      traces,
      total: 2,
      limit: 50,
      offset: 0,
    });

    renderTraceList();

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
    });
  });

  it("shows 'no traces match' when filter excludes all", async () => {
    const traces = [
      makeTrace({ trace_id: "t1", status: "ok" }),
    ];
    api.getTraces.mockResolvedValueOnce({
      traces,
      total: 1,
      limit: 50,
      offset: 0,
    });
    useTraceStore.setState({ traceFilter: { status: "error" } });

    renderTraceList();

    await waitFor(() => {
      expect(screen.getByText(/no traces match/i)).toBeInTheDocument();
    });
  });
});
