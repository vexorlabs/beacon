/**
 * Unified LLM pricing table and cost estimation.
 *
 * Mirror of Python SDK's beacon_sdk/pricing.py.
 * Prices are (input_cost_per_1M_tokens, output_cost_per_1M_tokens) in USD.
 * Keys are model name prefixes, ordered most-specific first.
 */

// [input_cost_per_1M, output_cost_per_1M]
const PRICE_TABLE: Array<[string, number, number]> = [
  // OpenAI — latest
  ["gpt-4.1-nano", 0.10, 0.40],
  ["gpt-4.1-mini", 0.40, 1.60],
  ["gpt-4.1", 2.00, 8.00],
  ["gpt-4o-mini", 0.15, 0.60],
  ["gpt-4o", 2.50, 10.00],
  ["o4-mini", 1.10, 4.40],
  ["o3-mini", 1.10, 4.40],
  ["o3", 2.00, 8.00],
  ["o1-mini", 3.00, 12.00],
  ["o1", 15.00, 60.00],
  // OpenAI — legacy
  ["gpt-4-turbo", 10.00, 30.00],
  ["gpt-4", 30.00, 60.00],
  ["gpt-3.5-turbo", 0.50, 1.50],
  // Anthropic — latest
  ["claude-opus-4", 5.00, 25.00],
  ["claude-sonnet-4", 3.00, 15.00],
  ["claude-haiku-4", 1.00, 5.00],
  // Anthropic — legacy
  ["claude-3-5-sonnet", 3.00, 15.00],
  ["claude-3-5-haiku", 1.00, 5.00],
  ["claude-3-opus", 15.00, 75.00],
  ["claude-3-sonnet", 3.00, 15.00],
  ["claude-3-haiku", 0.25, 1.25],
];

export function estimateCost(
  model: string,
  inputTokens: number,
  outputTokens: number
): number {
  for (const [prefix, inputPrice, outputPrice] of PRICE_TABLE) {
    if (model.startsWith(prefix)) {
      return (
        (inputTokens / 1_000_000) * inputPrice +
        (outputTokens / 1_000_000) * outputPrice
      );
    }
  }
  return 0.0;
}
