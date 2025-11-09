## DiffScribe Architecture Overview

### Components
- **GitHub Action Runner**: Executes on PR open/update events, authenticates using repo `GITHUB_TOKEN`, and invokes the DiffScribe workflow.
- **PR Fetcher (`diffscribe/github_client.py`)**: Uses PyGitHub to retrieve PR metadata, file diffs, and existing comments to maintain idempotency.
- **Diff Parser (`diffscribe/diff_parser/`)**: Converts raw PR diffs into a structured representation with per-file and per-function summaries for Python and JavaScript.
- **Risk Analyzer (`diffscribe/risk_analysis.py`)**: Applies heuristics to flag high-risk areas (core/shared modules), deprecated API usage, and missing tests.
- **LLM Summarizer (`diffscribe/llm_summarizer.py`)**: Calls OpenAI GPT APIs with structured diff data plus PR context to generate summaries, risk notes, and action items.
- **Output Orchestrator (`diffscribe/output_manager.py`)**: Formats the AI response, posts/updates PR comments, and optionally triggers living documentation creation.
- **Living Documentation (`docs/diffs/`)**: Optional Markdown artifacts generated per PR and committed back when enabled.

### Data Flow
1. GitHub Action receives PR event payload and exports metadata/`GITHUB_TOKEN`.
2. PR Fetcher gathers PR details and diffs via PyGitHub.
3. Diff Parser builds a language-aware representation for downstream consumers.
4. Risk Analyzer annotates the diff structure with risk signals.
5. LLM Summarizer prompts OpenAI with the structured diff + risks + PR description.
6. Output Orchestrator posts/updates the PR comment and handles living docs.

### Storage & Secrets
- **Secrets**: `GITHUB_TOKEN` for GitHub API access; `OPENAI_API_KEY` stored as repo secret.
- **Artifacts**: Optional Markdown docs under `docs/diffs/` committed via the action.

