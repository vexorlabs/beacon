import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { observe } from "../src/decorators.js";
import { _setTracerGetter } from "../src/decorators.js";
import { BeaconTracer } from "../src/tracer.js";
import { InMemoryExporter } from "./helpers.js";

describe("observe", () => {
  let exporter: InMemoryExporter;
  let tracer: BeaconTracer;

  beforeEach(() => {
    exporter = new InMemoryExporter();
    tracer = new BeaconTracer({ exporter, enabled: true });
    _setTracerGetter(() => tracer);
  });

  afterEach(() => {
    _setTracerGetter(() => null);
  });

  it("wraps a sync function and creates a span", () => {
    function add(a: number, b: number): number {
      return a + b;
    }
    const traced = observe(add);
    const result = traced(2, 3);

    expect(result).toBe(5);
    expect(exporter.spans).toHaveLength(1);
    expect(exporter.spans[0]!.name).toBe("add");
    expect(exporter.spans[0]!.status).toBe("ok");
  });

  it("wraps an async function and creates a span", async () => {
    async function fetchData(): Promise<string> {
      return "data";
    }
    const traced = observe(fetchData);
    const result = await traced();

    expect(result).toBe("data");
    expect(exporter.spans).toHaveLength(1);
    expect(exporter.spans[0]!.status).toBe("ok");
  });

  it("captures errors from sync functions", () => {
    function failing(): never {
      throw new Error("oops");
    }
    const traced = observe(failing);

    expect(() => traced()).toThrow("oops");
    expect(exporter.spans[0]!.status).toBe("error");
    expect(exporter.spans[0]!.error_message).toBe("oops");
  });

  it("captures errors from async functions", async () => {
    async function failing(): Promise<never> {
      throw new Error("async oops");
    }
    const traced = observe(failing);

    await expect(traced()).rejects.toThrow("async oops");
    expect(exporter.spans[0]!.status).toBe("error");
  });

  it("uses custom name and spanType from options", () => {
    const fn = observe({ name: "my-agent", spanType: "agent_step" }, () => {
      return true;
    });
    fn();

    expect(exporter.spans[0]!.name).toBe("my-agent");
    expect(exporter.spans[0]!.span_type).toBe("agent_step");
  });

  it("falls through when no tracer is configured", () => {
    _setTracerGetter(() => null);
    function plain(): number {
      return 99;
    }
    const traced = observe(plain);
    expect(traced()).toBe(99);
    expect(exporter.spans).toHaveLength(0);
  });

  it("uses 'anonymous' name for unnamed functions", () => {
    const traced = observe(() => "anon");
    traced();

    expect(exporter.spans[0]!.name).toBe("anonymous");
  });
});
