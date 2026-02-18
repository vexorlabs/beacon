"""Hardcoded realistic data for Beacon demo agents.

All LLM completions, tool results, shell output, and fake screenshots
used by the demo scripts are defined here. Edit this file to change
what the demos produce.
"""

from __future__ import annotations

import json

# =============================================================================
# Shared constants
# =============================================================================

# Minimal valid 1x1 white PNG, base64-encoded.
TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


# =============================================================================
# Scenario 1: Research Agent
# =============================================================================

RESEARCH_SYSTEM_PROMPT = (
    "You are a research assistant. Break down complex questions into steps, "
    "search for information, and synthesize findings into clear reports."
)

RESEARCH_USER_QUERY = "What caused the 2008 financial crisis?"

RESEARCH_PLAN_COMPLETION = (
    "I'll research the 2008 financial crisis in 4 steps:\n"
    "1. Search for key events and timeline of the crisis\n"
    "2. Find primary sources on mortgage-backed securities and CDOs\n"
    "3. Analyze the role of regulatory failures\n"
    "4. Synthesize findings into a structured report"
)

RESEARCH_SEARCH_RESULTS = json.dumps(
    [
        {
            "title": "The Financial Crisis of 2008: Year In Review",
            "url": "https://www.britannica.com/topic/financial-crisis-of-2008",
            "snippet": "The 2008 financial crisis was the worst economic disaster since the Great Depression of 1929.",
        },
        {
            "title": "Causes of the 2008 Financial Crisis",
            "url": "https://www.investopedia.com/articles/economics/09/financial-crisis-review.asp",
            "snippet": "Deregulation in the financial industry was a key factor enabling risky lending practices.",
        },
        {
            "title": "The Big Short: Inside the Doomsday Machine",
            "url": "https://en.wikipedia.org/wiki/The_Big_Short",
            "snippet": "Michael Lewis documented how a few investors predicted the collapse of the housing bubble.",
        },
    ],
    indent=2,
)

RESEARCH_ARTICLE_CONTENT = (
    "The 2008 financial crisis had its roots in the U.S. housing market. Starting in "
    "the early 2000s, a combination of low interest rates, relaxed lending standards, and "
    "financial innovation created a housing bubble. Banks issued subprime mortgages to "
    "borrowers with poor credit histories, then packaged these mortgages into complex "
    "financial instruments called mortgage-backed securities (MBS) and collateralized debt "
    "obligations (CDOs).\n\n"
    "Rating agencies like Moody's and S&P assigned AAA ratings to many of these instruments, "
    "masking their underlying risk. When housing prices began to fall in 2006-2007, the "
    "value of these securities plummeted. Financial institutions that held large positions "
    "in MBS and CDOs—including Bear Stearns, Lehman Brothers, and AIG—faced massive losses.\n\n"
    "The crisis reached its peak in September 2008 when Lehman Brothers filed for bankruptcy, "
    "the largest in U.S. history. The resulting panic froze credit markets worldwide, leading "
    "to a severe global recession."
)

RESEARCH_SYNTHESIS_TOOL_CALLS = json.dumps(
    [
        {
            "id": "call_synth_001",
            "function": {
                "name": "web_search",
                "arguments": json.dumps(
                    {"query": "2008 crisis regulatory response Dodd-Frank"}
                ),
            },
        }
    ]
)

RESEARCH_SYNTHESIS_COMPLETION = (
    "Based on my research, the 2008 financial crisis was caused by a convergence of factors:\n\n"
    "**Root Causes:**\n"
    "- Widespread issuance of subprime mortgages to unqualified borrowers\n"
    "- Bundling of risky mortgages into complex CDOs and MBS\n"
    "- Rating agencies assigning AAA ratings to high-risk instruments\n"
    "- Excessive leverage at major financial institutions (30:1 ratios)\n"
    "- Regulatory gaps in oversight of the shadow banking system\n\n"
    "**Key Events:**\n"
    "- 2006-2007: Housing prices begin to decline\n"
    "- March 2008: Bear Stearns collapses, acquired by JPMorgan\n"
    "- September 2008: Lehman Brothers files for bankruptcy\n"
    "- September 2008: AIG receives $85B government bailout\n"
    "- October 2008: Congress passes $700B TARP bailout\n\n"
    "**Aftermath:**\n"
    "The crisis led to the Great Recession, with global GDP declining 2.1% in 2009. "
    "Regulatory reforms including the Dodd-Frank Act were enacted to prevent a recurrence."
)

RESEARCH_REPORT_COMPLETION = (
    "# The 2008 Financial Crisis: Causes and Consequences\n\n"
    "## Executive Summary\n"
    "The 2008 financial crisis was the most severe global economic downturn since the "
    "Great Depression, triggered by the collapse of the U.S. housing bubble and amplified "
    "by systemic failures in financial regulation and risk management.\n\n"
    "## Key Findings\n"
    "1. Subprime lending practices created a $1.3 trillion bubble in mortgage debt\n"
    "2. Financial engineering (CDOs, CDS) obscured and amplified risk\n"
    "3. Rating agencies failed in their gatekeeping role\n"
    "4. Regulatory fragmentation left critical gaps in oversight\n"
    "5. Excessive leverage made the system fragile to price corrections\n\n"
    "## Recommendations\n"
    "- Strengthen capital requirements for systemically important institutions\n"
    "- Improve transparency in derivatives markets\n"
    "- Reform rating agency incentive structures\n"
    "- Establish macro-prudential oversight mechanisms"
)


# =============================================================================
# Scenario 2: Code Writer Agent
# =============================================================================

CODE_WRITER_SYSTEM_PROMPT = (
    "You are a senior Python developer. Write clean, well-tested code. "
    "When tests fail, analyze the error and fix the issue."
)

CODE_WRITER_USER_REQUEST = (
    "Write a Python function to parse CSV files with support for "
    "custom delimiters and header detection."
)

CODE_WRITER_REQUIREMENTS_COMPLETION = (
    "I'll implement a CSV parser with these features:\n"
    "1. Support for custom delimiters (comma, tab, pipe, etc.)\n"
    "2. Automatic header detection from the first row\n"
    "3. Return data as a list of dictionaries\n"
    "4. Handle quoted fields and escaped characters\n"
    "5. Proper error handling for malformed files"
)

CODE_WRITER_INITIAL_CODE = '''\
def parse_csv(filepath: str, delimiter: str = ",", has_header: bool = True) -> list[dict[str, str]]:
    """Parse a CSV file and return rows as dictionaries."""
    rows: list[dict[str, str]] = []
    with open(filepath, "r") as f:
        lines = f.readlines()

    if not lines:
        return rows

    if has_header:
        headers = [h.strip() for h in lines[0].split(delimiter)]
        data_lines = lines[1:]
    else:
        first_row = lines[0].split(delimiter)
        headers = [f"col_{i}" for i in range(len(first_row))]
        data_lines = lines

    for line in data_lines:
        values = [v.strip() for v in line.split(delimiter)]
        row = dict(zip(headers, values))
        rows.append(row)

    return rows
'''

CODE_WRITER_SAVE_OUTPUT = "Wrote 24 lines to csv_parser.py"

CODE_WRITER_FAILING_TEST_OUTPUT = (
    "============================= test session starts ==============================\n"
    "platform linux -- Python 3.11.5, pytest-7.4.3\n"
    "collected 5 items\n\n"
    "test_csv_parser.py::test_basic_csv PASSED                               [ 20%]\n"
    "test_csv_parser.py::test_custom_delimiter PASSED                        [ 40%]\n"
    "test_csv_parser.py::test_no_header PASSED                               [ 60%]\n"
    "test_csv_parser.py::test_empty_file FAILED                              [ 80%]\n"
    "test_csv_parser.py::test_quoted_fields PASSED                           [100%]\n\n"
    "=================================== FAILURES ===================================\n"
    "_______________________________ test_empty_file ________________________________\n\n"
    "    def test_empty_file(tmp_path):\n"
    '        csv_file = tmp_path / "empty.csv"\n'
    '        csv_file.write_text("")\n'
    "        result = parse_csv(str(csv_file))\n"
    ">       assert result == []\n"
    "E       IndexError: list index out of range\n\n"
    "test_csv_parser.py:28: IndexError\n"
    "=========================== short test summary info ============================\n"
    "FAILED test_csv_parser.py::test_empty_file - IndexError: list index out of range\n"
    "========================= 1 failed, 4 passed in 0.12s ========================="
)

CODE_WRITER_DEBUG_COMPLETION = (
    "The test_empty_file test is failing because when the file is empty, `lines` is an "
    "empty list, but we still try to access `lines[0]` to parse headers. The fix is to "
    "add an early return check:\n\n"
    "```python\n"
    "if not lines:\n"
    "    return rows\n"
    "```\n\n"
    "Wait—that check already exists. The issue is that `lines` contains `['']` (a list "
    "with one empty string) when the file is empty, not `[]`. I need to strip whitespace "
    "and filter empty lines:\n\n"
    "```python\n"
    "lines = [l for l in f.readlines() if l.strip()]\n"
    "```"
)

CODE_WRITER_FIX_OUTPUT = (
    "Applied fix to csv_parser.py:\n"
    "  - Line 5: lines = [l for l in f.readlines() if l.strip()]\n"
    "  + Added empty line filtering"
)

CODE_WRITER_PASSING_TEST_OUTPUT = (
    "============================= test session starts ==============================\n"
    "platform linux -- Python 3.11.5, pytest-7.4.3\n"
    "collected 5 items\n\n"
    "test_csv_parser.py::test_basic_csv PASSED                               [ 20%]\n"
    "test_csv_parser.py::test_custom_delimiter PASSED                        [ 40%]\n"
    "test_csv_parser.py::test_no_header PASSED                               [ 60%]\n"
    "test_csv_parser.py::test_empty_file PASSED                              [ 80%]\n"
    "test_csv_parser.py::test_quoted_fields PASSED                           [100%]\n\n"
    "========================= 5 passed in 0.08s ==================================="
)

CODE_WRITER_DOCS_COMPLETION = (
    '"""CSV Parser Module\n\n'
    "Parse CSV files with support for custom delimiters and automatic header detection.\n\n"
    "Functions:\n"
    "    parse_csv(filepath, delimiter, has_header) -> list[dict[str, str]]\n\n"
    "Example:\n"
    "    >>> rows = parse_csv('data.csv', delimiter='|')\n"
    "    >>> print(rows[0]['name'])\n"
    '    \'Alice\'\n'
    '"""'
)


# =============================================================================
# Scenario 3: Web Scraper Agent
# =============================================================================

SCRAPER_SYSTEM_PROMPT = (
    "You are a web scraping assistant. Navigate to websites, extract structured data, "
    "and handle errors gracefully when pages are unavailable."
)

SCRAPER_USER_QUERY = "Scrape the top 3 headlines from Hacker News"

SCRAPER_PLAN_COMPLETION = (
    "I'll scrape Hacker News headlines with this approach:\n"
    "1. Navigate to https://news.ycombinator.com\n"
    "2. Wait for the main content to load\n"
    "3. Take a screenshot for reference\n"
    "4. Extract headline text and URLs from .titleline elements\n"
    "5. Visit each article to get additional metadata\n"
    "6. Compile results into structured data"
)

SCRAPER_HEADLINES_JSON = json.dumps(
    [
        {
            "rank": 1,
            "title": "Show HN: I built a local-first debugging platform for AI agents",
            "url": "https://github.com/example/beacon",
            "points": 342,
            "comments": 127,
        },
        {
            "rank": 2,
            "title": "SQLite is not a toy database",
            "url": "https://antonz.org/sqlite-is-not-a-toy-database/",
            "points": 289,
            "comments": 95,
        },
        {
            "rank": 3,
            "title": "The unreasonable effectiveness of simple HTML",
            "url": "https://whitep4nth3r.com/blog/simple-html/",
            "points": 201,
            "comments": 63,
        },
    ],
    indent=2,
)

SCRAPER_PARSE_TOOL_CALLS = json.dumps(
    [
        {
            "id": "call_parse_001",
            "function": {
                "name": "extract_structured_data",
                "arguments": json.dumps(
                    {
                        "selector": ".titleline > a",
                        "fields": ["text", "href"],
                        "limit": 3,
                    }
                ),
            },
        }
    ]
)

SCRAPER_PARSE_COMPLETION = (
    "I've extracted 3 headlines from the page. Here are the structured results:\n\n"
    "1. **Show HN: I built a local-first debugging platform for AI agents** (342 points)\n"
    "2. **SQLite is not a toy database** (289 points)\n"
    "3. **The unreasonable effectiveness of simple HTML** (201 points)\n\n"
    "Let me visit each article to get more details."
)

SCRAPER_RESULTS_COMPLETION = (
    "## Hacker News Top 3 Headlines\n\n"
    "### 1. Show HN: I built a local-first debugging platform for AI agents\n"
    "- URL: https://github.com/example/beacon\n"
    "- Points: 342 | Comments: 127\n"
    "- Category: Show HN / Developer Tools\n\n"
    "### 2. SQLite is not a toy database\n"
    "- URL: https://antonz.org/sqlite-is-not-a-toy-database/\n"
    "- Points: 289 | Comments: 95\n"
    "- Category: Databases / Opinion\n\n"
    "### 3. The unreasonable effectiveness of simple HTML\n"
    "- URL: https://whitep4nth3r.com/blog/simple-html/\n"
    "- Points: 201 | Comments: 63\n"
    "- Category: Web Development / Opinion\n\n"
    "Note: Article #3 could not be visited due to a connection timeout. "
    "Data shown is from the Hacker News listing only."
)


# =============================================================================
# Scenario 4: RAG Pipeline
# =============================================================================

RAG_USER_QUERY = (
    "What are the key differences between transformers and traditional RNNs "
    "for sequence modeling?"
)

RAG_EMBEDDING_PROMPT = json.dumps(
    [{"role": "user", "content": RAG_USER_QUERY}]
)

RAG_SEARCH_RESULTS = json.dumps(
    [
        {
            "chunk_id": "doc_17_chunk_3",
            "score": 0.92,
            "text": (
                "Transformers replace recurrence with self-attention, allowing parallel "
                "computation across all positions in a sequence. Unlike RNNs which process "
                "tokens sequentially, transformers compute attention scores between every "
                "pair of positions simultaneously."
            ),
            "source": "attention_is_all_you_need.pdf",
        },
        {
            "chunk_id": "doc_42_chunk_1",
            "score": 0.87,
            "text": (
                "RNNs suffer from vanishing gradients when processing long sequences. "
                "LSTMs and GRUs partially address this with gating mechanisms, but still "
                "struggle with dependencies beyond ~1000 tokens. Transformers handle "
                "arbitrary-length dependencies through positional encodings and attention."
            ),
            "source": "deep_learning_survey_2023.pdf",
        },
        {
            "chunk_id": "doc_8_chunk_5",
            "score": 0.81,
            "text": (
                "The computational complexity of self-attention is O(n^2) in sequence length, "
                "compared to O(n) for RNNs. However, transformers are more parallelizable "
                "and achieve better hardware utilization on modern GPUs. Recent work on "
                "linear attention and sparse attention reduces this to O(n log n) or O(n)."
            ),
            "source": "efficient_transformers.pdf",
        },
    ],
    indent=2,
)

RAG_SCORE_COMPLETIONS = [
    "Relevance: HIGH (0.95). This chunk directly addresses the core architectural difference—self-attention vs recurrence. It explains the parallelization advantage clearly.",
    "Relevance: HIGH (0.88). This chunk covers the vanishing gradient problem in RNNs and how transformers address it. Directly relevant to the comparison question.",
    "Relevance: MEDIUM (0.72). This chunk focuses on computational complexity trade-offs. Relevant but more technical than what the question asks for.",
]

RAG_CONTEXT_OUTPUT = json.dumps(
    {
        "num_chunks": 3,
        "total_tokens": 487,
        "sources": [
            "attention_is_all_you_need.pdf",
            "deep_learning_survey_2023.pdf",
            "efficient_transformers.pdf",
        ],
    },
    indent=2,
)

RAG_ANSWER_COMPLETION = (
    "## Transformers vs Traditional RNNs for Sequence Modeling\n\n"
    "The key differences between transformers and traditional RNNs center on three areas:\n\n"
    "### 1. Attention vs Recurrence\n"
    "Transformers replace sequential recurrence with **self-attention**, computing "
    "relationships between all positions in a sequence simultaneously. RNNs process "
    "tokens one at a time, maintaining a hidden state that is updated at each step. "
    "This fundamental architectural difference has profound implications for both "
    "training efficiency and model capability.\n\n"
    "### 2. Long-Range Dependencies\n"
    "RNNs struggle with **vanishing gradients** when sequences exceed ~1000 tokens, "
    "even with LSTM or GRU gating mechanisms. Transformers handle arbitrary-length "
    "dependencies through positional encodings and direct attention connections "
    "between any two positions, regardless of distance.\n\n"
    "### 3. Parallelization\n"
    "RNN computation is inherently **sequential** — each token depends on the previous "
    "hidden state. Transformers are fully parallelizable during training, achieving "
    "much better GPU utilization. The trade-off is O(n^2) memory for self-attention "
    "vs O(n) for RNNs, though techniques like sparse and linear attention reduce this.\n\n"
    "### Summary\n"
    "Transformers dominate modern NLP due to superior parallelization and long-range "
    "modeling, while RNNs retain advantages for streaming and low-latency applications "
    "where sequential processing is acceptable.\n\n"
    "*Sources: Vaswani et al. (2017), Deep Learning Survey (2023), Efficient Transformers Review*"
)

RAG_VERIFICATION_COMPLETION = (
    "Verification check:\n"
    "- [PASS] Answer addresses all three key differences requested\n"
    "- [PASS] Claims are supported by the retrieved chunks\n"
    "- [PASS] No hallucinated facts — all statements trace to source documents\n"
    "- [PASS] Balanced perspective — mentions trade-offs for both architectures\n"
    "- [PASS] Technical accuracy — O(n^2) complexity, vanishing gradients, parallelization claims are correct\n\n"
    "Confidence: HIGH. The answer is well-supported by the retrieved context."
)
