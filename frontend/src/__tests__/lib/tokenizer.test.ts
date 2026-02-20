import { describe, it, expect } from "vitest";
import { countTokens } from "@/lib/tokenizer";

describe("countTokens", () => {
  it("returns 0 for empty string", () => {
    expect(countTokens("")).toBe(0);
  });

  it("returns a positive number for non-empty text", () => {
    const count = countTokens("Hello, world!");
    expect(count).toBeGreaterThan(0);
  });

  it("counts tokens for a typical prompt", () => {
    const prompt = JSON.stringify([
      { role: "system", content: "You are a helpful assistant." },
      { role: "user", content: "What is the capital of France?" },
    ]);
    const count = countTokens(prompt);
    // A prompt like this should be roughly 30-60 tokens
    expect(count).toBeGreaterThan(10);
    expect(count).toBeLessThan(200);
  });

  it("handles very long strings without throwing", () => {
    const longText = "word ".repeat(10000);
    expect(() => countTokens(longText)).not.toThrow();
    expect(countTokens(longText)).toBeGreaterThan(0);
  });
});
