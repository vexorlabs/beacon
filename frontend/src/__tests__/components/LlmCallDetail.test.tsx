import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { makeSpan, resetFixtures } from "@/test/fixtures";

// Mock Monaco editor (heavy, requires DOM)
vi.mock("@monaco-editor/react", () => ({
  default: ({ value }: { value: string }) => (
    <textarea data-testid="monaco-mock" defaultValue={value} />
  ),
}));

// Mock the API and store
vi.mock("@/lib/api", () => ({
  getTraces: vi.fn(),
  getTrace: vi.fn(),
  getTraceGraph: vi.fn(),
  postReplay: vi.fn(),
  deleteTrace: vi.fn(),
}));

const { default: LlmCallDetail } = await import(
  "@/components/SpanDetail/LlmCallDetail"
);

beforeEach(() => {
  resetFixtures();
});

describe("LlmCallDetail", () => {
  it("renders provider and model badges", () => {
    const span = makeSpan({
      attributes: {
        "llm.provider": "openai",
        "llm.model": "gpt-4o",
        "llm.prompt": "[]",
        "llm.completion": "Hello",
        "llm.tokens.input": 10,
        "llm.tokens.output": 5,
        "llm.cost_usd": 0.001,
      },
    });

    render(<LlmCallDetail span={span} />);

    expect(screen.getByText("openai")).toBeInTheDocument();
    expect(screen.getByText("gpt-4o")).toBeInTheDocument();
  });

  it("renders token counts and cost", () => {
    const span = makeSpan({
      attributes: {
        "llm.tokens.input": 1500,
        "llm.tokens.output": 200,
        "llm.cost_usd": 0.0234,
        "llm.prompt": "[]",
        "llm.completion": "result",
      },
    });

    render(<LlmCallDetail span={span} />);

    expect(screen.getByText("1,500")).toBeInTheDocument();
    expect(screen.getByText("200")).toBeInTheDocument();
    expect(screen.getByText("$0.0234")).toBeInTheDocument();
  });

  it("renders prompt messages when llm.prompt is JSON array", () => {
    const messages = [
      { role: "system", content: "You are helpful" },
      { role: "user", content: "Hello there" },
    ];
    const span = makeSpan({
      attributes: {
        "llm.prompt": JSON.stringify(messages),
        "llm.completion": "Hi!",
      },
    });

    render(<LlmCallDetail span={span} />);

    expect(screen.getByText("system")).toBeInTheDocument();
    expect(screen.getByText("You are helpful")).toBeInTheDocument();
    expect(screen.getByText("user")).toBeInTheDocument();
    expect(screen.getByText("Hello there")).toBeInTheDocument();
  });

  it("renders completion text", () => {
    const span = makeSpan({
      attributes: {
        "llm.prompt": "[]",
        "llm.completion": "The answer is 42",
      },
    });

    render(<LlmCallDetail span={span} />);

    expect(screen.getByText("The answer is 42")).toBeInTheDocument();
  });

  it("handles missing attributes gracefully", () => {
    const span = makeSpan({ attributes: {} });

    render(<LlmCallDetail span={span} />);

    // Should show "—" for missing numeric values
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it("renders tool calls section when present", () => {
    const toolCalls = [
      {
        function: {
          name: "search",
          arguments: '{"query": "test"}',
        },
      },
    ];
    const span = makeSpan({
      attributes: {
        "llm.prompt": "[]",
        "llm.completion": "result",
        "llm.tool_calls": JSON.stringify(toolCalls),
      },
    });

    render(<LlmCallDetail span={span} />);

    expect(screen.getByText("search")).toBeInTheDocument();
  });
});
