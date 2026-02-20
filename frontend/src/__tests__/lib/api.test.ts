import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getTraces,
  getTrace,
  getTraceGraph,
  postReplay,
  deleteTrace,
  searchTraces,
  getStats,
  exportTrace,
} from "@/lib/api";

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

function jsonResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(data),
    blob: () => Promise.resolve(new Blob([JSON.stringify(data)])),
  } as Response;
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api", () => {
  describe("getTraces", () => {
    it("fetches /v1/traces with no params", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ traces: [], total: 0, limit: 50, offset: 0 }),
      );

      const result = await getTraces();

      expect(mockFetch).toHaveBeenCalledWith("/v1/traces", undefined);
      expect(result.traces).toEqual([]);
    });

    it("includes query params when provided", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ traces: [], total: 0, limit: 10, offset: 5 }),
      );

      await getTraces({ limit: 10, offset: 5, status: "error" });

      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain("limit=10");
      expect(url).toContain("offset=5");
      expect(url).toContain("status=error");
    });
  });

  describe("getTrace", () => {
    it("fetches /v1/traces/{traceId}", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ trace_id: "abc", spans: [] }),
      );

      await getTrace("abc");

      expect(mockFetch).toHaveBeenCalledWith("/v1/traces/abc", undefined);
    });
  });

  describe("getTraceGraph", () => {
    it("fetches /v1/traces/{traceId}/graph", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ nodes: [], edges: [] }),
      );

      await getTraceGraph("abc");

      expect(mockFetch).toHaveBeenCalledWith(
        "/v1/traces/abc/graph",
        undefined,
      );
    });
  });

  describe("postReplay", () => {
    it("sends POST with JSON body", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ replay_id: "r1" }),
      );

      await postReplay({
        span_id: "s1",
        modified_attributes: { "llm.prompt": "test" },
      });

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe("/v1/replay");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body as string)).toEqual({
        span_id: "s1",
        modified_attributes: { "llm.prompt": "test" },
      });
    });
  });

  describe("deleteTrace", () => {
    it("sends DELETE request", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ deleted_count: 1 }),
      );

      await deleteTrace("t1");

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe("/v1/traces/t1");
      expect(init.method).toBe("DELETE");
    });
  });

  describe("searchTraces", () => {
    it("constructs correct URL with query and params", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ results: [], total: 0 }),
      );

      await searchTraces("error", { limit: 5 });

      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain("q=error");
      expect(url).toContain("limit=5");
    });
  });

  describe("getStats", () => {
    it("fetches /v1/stats", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ total_traces: 10 }),
      );

      await getStats();

      expect(mockFetch).toHaveBeenCalledWith("/v1/stats", undefined);
    });
  });

  describe("exportTrace", () => {
    it("fetches trace export as blob", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ data: "csv-content" }),
      );

      const result = await exportTrace("t1", "csv");

      expect(mockFetch).toHaveBeenCalledWith(
        "/v1/traces/t1/export?format=csv",
      );
      expect(result).toBeInstanceOf(Blob);
    });
  });

  describe("error handling", () => {
    it("throws with detail message from error response", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: "Not found" }, 404),
      );

      await expect(getTrace("missing")).rejects.toThrow("Not found");
    });

    it("throws with HTTP status when no detail", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse(null, 500),
      );

      await expect(getTrace("bad")).rejects.toThrow("HTTP 500");
    });
  });
});
