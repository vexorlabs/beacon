import { describe, it, expect } from "vitest";
import { estimateCost } from "../src/pricing.js";

describe("estimateCost", () => {
  it("calculates cost for gpt-4o", () => {
    // 1000 input tokens at $2.50/1M = $0.0025
    // 500 output tokens at $10.00/1M = $0.005
    const cost = estimateCost("gpt-4o", 1000, 500);
    expect(cost).toBeCloseTo(0.0075, 6);
  });

  it("calculates cost for gpt-4o-mini (prefix match before gpt-4o)", () => {
    // 1000 input at $0.15/1M = $0.00015
    // 500 output at $0.60/1M = $0.0003
    const cost = estimateCost("gpt-4o-mini", 1000, 500);
    expect(cost).toBeCloseTo(0.00045, 6);
  });

  it("calculates cost for claude-sonnet-4 model variants", () => {
    // Prefix match: "claude-sonnet-4-6-20250514" matches "claude-sonnet-4"
    const cost = estimateCost("claude-sonnet-4-6-20250514", 1000, 500);
    // 1000 input at $3.00/1M = $0.003
    // 500 output at $15.00/1M = $0.0075
    expect(cost).toBeCloseTo(0.0105, 6);
  });

  it("returns 0 for unknown models", () => {
    expect(estimateCost("unknown-model", 1000, 500)).toBe(0);
  });

  it("returns 0 for zero tokens", () => {
    expect(estimateCost("gpt-4o", 0, 0)).toBe(0);
  });

  it("calculates cost for gpt-4.1", () => {
    // 1M input at $2.00 + 1M output at $8.00 = $10.00
    const cost = estimateCost("gpt-4.1", 1_000_000, 1_000_000);
    expect(cost).toBeCloseTo(10.0, 2);
  });
});
