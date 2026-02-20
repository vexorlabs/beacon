import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { HttpSpanExporter, BatchExporter } from "../src/exporter.js";
import { Span, SpanType } from "../src/models.js";

function makeSpan(name = "test"): Span {
  const span = new Span({ trace_id: "t1", name, span_type: SpanType.CUSTOM });
  span.end();
  return span;
}

describe("HttpSpanExporter", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts spans to the correct endpoint", async () => {
    const exporter = new HttpSpanExporter("http://localhost:7474");
    const span = makeSpan();
    exporter.export([span]);

    // Wait for fire-and-forget fetch to complete
    await vi.waitFor(() => expect(fetchSpy).toHaveBeenCalledOnce());

    const [url, options] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:7474/v1/spans");
    expect(options.method).toBe("POST");
    expect(options.headers).toEqual({ "Content-Type": "application/json" });

    const body = JSON.parse(options.body as string) as { spans: unknown[] };
    expect(body.spans).toHaveLength(1);
  });

  it("strips trailing slashes from backend URL", async () => {
    const exporter = new HttpSpanExporter("http://localhost:7474///");
    exporter.export([makeSpan()]);

    await vi.waitFor(() => expect(fetchSpy).toHaveBeenCalledOnce());
    expect(fetchSpy.mock.calls[0]![0]).toBe("http://localhost:7474/v1/spans");
  });

  it("silently handles fetch failures", () => {
    fetchSpy.mockRejectedValue(new Error("network error"));
    const exporter = new HttpSpanExporter("http://localhost:7474");
    expect(() => exporter.export([makeSpan()])).not.toThrow();
  });
});

describe("BatchExporter", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchSpy);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("batches spans and flushes on interval", async () => {
    const exporter = new BatchExporter({
      backendUrl: "http://localhost:7474",
      flushIntervalMs: 100,
    });

    exporter.export([makeSpan("s1")]);
    exporter.export([makeSpan("s2")]);

    expect(fetchSpy).not.toHaveBeenCalled();

    // Advance timer to trigger flush
    vi.advanceTimersByTime(100);
    // Wait for async flush
    await vi.waitFor(() => expect(fetchSpy).toHaveBeenCalledOnce());

    const body = JSON.parse(
      (fetchSpy.mock.calls[0] as [string, RequestInit])[1].body as string
    ) as { spans: unknown[] };
    expect(body.spans).toHaveLength(2);

    await exporter.shutdown();
  });

  it("flushes when batch size is reached", async () => {
    const exporter = new BatchExporter({
      backendUrl: "http://localhost:7474",
      batchSize: 2,
      flushIntervalMs: 60_000,
    });

    exporter.export([makeSpan("s1")]);
    expect(fetchSpy).not.toHaveBeenCalled();

    exporter.export([makeSpan("s2")]); // triggers batch flush

    await vi.waitFor(() => expect(fetchSpy).toHaveBeenCalledOnce());

    await exporter.shutdown();
  });

  it("flushes remaining spans on shutdown", async () => {
    vi.useRealTimers(); // Need real timers for shutdown await
    fetchSpy = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchSpy);

    const exporter = new BatchExporter({
      backendUrl: "http://localhost:7474",
      flushIntervalMs: 60_000,
    });

    exporter.export([makeSpan()]);
    await exporter.shutdown();

    expect(fetchSpy).toHaveBeenCalledOnce();
  });

  it("manual flush sends all queued spans", async () => {
    vi.useRealTimers();
    fetchSpy = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchSpy);

    const exporter = new BatchExporter({
      backendUrl: "http://localhost:7474",
      flushIntervalMs: 60_000,
    });

    exporter.export([makeSpan()]);
    await exporter.flush();

    expect(fetchSpy).toHaveBeenCalledOnce();
    await exporter.shutdown();
  });
});
