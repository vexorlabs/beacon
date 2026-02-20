import { getEncoding, type Tiktoken } from "js-tiktoken";

let encoding: Tiktoken | null = null;

function getOrCreateEncoding(): Tiktoken {
  if (!encoding) {
    encoding = getEncoding("cl100k_base");
  }
  return encoding;
}

/**
 * Count tokens in text using cl100k_base encoding.
 * Falls back to a rough character-based estimate on error.
 */
export function countTokens(text: string): number {
  if (!text) return 0;
  try {
    return getOrCreateEncoding().encode(text).length;
  } catch {
    return Math.ceil(text.length / 4);
  }
}
