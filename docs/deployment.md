## DiffScribe Deployment Checklist

### 1. Prerequisites
- Python 3.11+ available locally (for debugging or dry runs).
- OpenAI API key with access to `gpt-4o-mini` (or update `diffscribe/llm_summarizer.py` with preferred model).
- Repository maintainer access to configure GitHub secrets/variables.

### 2. GitHub Secrets & Variables
| Name | Type | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Secret | Authenticates OpenAI requests. |
| `DIFFSCRIBE_ENABLE_LIVING_DOCS` | Variable (optional) | `true` enables `/docs/diffs/PR_<number>.md` generation. |
| `DIFFSCRIBE_COMMIT_LIVING_DOCS` | Variable (optional) | `true` commits/pushes living docs during workflow run. |

> No extra PAT required: the built-in `secrets.GITHUB_TOKEN` powers PR reads, comments, and optional doc commits.

### 3. Workflow Installation
The repository already includes `.github/workflows/diffs-scribe.yml`. Ensure it is committed to `main`. On PR events (`opened`, `synchronize`, `reopened`, `ready_for_review`, `edited`) it will:
1. Install dependencies.
2. Execute `python -m diffscribe.cli`.
3. Upload the JSON analysis artifact.
4. Post or update the DiffScribe PR comment.
5. (Optional) Commit and push living docs.

### 4. Local Validation (Optional)
1. Capture a PR event payload (`.github/workflows` → **View Run** → **Download workflow run artifacts** → `event.json`).
2. Run locally:
   ```bash
   python -m diffscribe.cli --event-path event.json --output artifacts/test.json --skip-comment
   ```
3. Inspect `artifacts/test.json` for the structured analysis result.

### 5. Release Notes Template
When publishing a release/tag, include:
- ✅ Supported languages (Python, JavaScript)
- ✅ Risk heuristics summary
- ✅ How to enable living docs
- 🔜 Roadmap (multi-language, Slack, dashboards)

### 6. Post-Deployment Monitoring
- Watch PR comments to confirm DiffScribe posts as expected.
- Check GitHub Action run logs for OpenAI or Git issues.
- Audit living doc commits if enabled.

### 7. Future Enhancements
- Add configurable risk profiles per repo.
- Support additional LLM providers.
- Introduce PR label triggers (e.g., run only when `needs-ai-review` is present).
- Integrate with chat platforms for reviewer alerts.

