## DiffScribe

DiffScribe is an AI-assisted pull request reviewer that summarizes intent, highlights risk, and (optionally) publishes living documentation for every PR.

### Features
- GitHub Action triggered on PR open/update.
- Diff parsing for Python and JavaScript with function-level summaries.
- Heuristic risk analysis for high-impact files, missing tests, and deprecated APIs.
- OpenAI-powered summaries with behavior changes, risks, and suggested actions.
- PR comment upsert to keep reviewers in sync.
- Optional living documentation at `docs/diffs/PR_<number>.md` with optional auto-commit.

### Quick Start
1. Install dependencies locally:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Export secrets for local runs:
   ```bash
   export GITHUB_TOKEN=<personal-access-token>
   export OPENAI_API_KEY=<openai-key>
   ```
3. Execute the workflow script against a GitHub event payload:
   ```bash
   python -m diffscribe.cli --event-path path/to/event.json --output artifacts/pr_snapshot.json --skip-comment
   ```

### GitHub Action Setup
1. Copy `.github/workflows/diffs-scribe.yml` into your repository (already included here).
2. Configure repository secrets:
   - `OPENAI_API_KEY`: OpenAI API key for GPT access.
3. (Optional) Configure repository variables to toggle living docs:
   - `DIFFSCRIBE_ENABLE_LIVING_DOCS` → `true` to write docs.
   - `DIFFSCRIBE_COMMIT_LIVING_DOCS` → `true` to auto-commit/push docs.

> **Note:** The Action already has access to `secrets.GITHUB_TOKEN`, which is sufficient for API reads/writes within the repository.

### Living Documentation
- Enable via `ENABLE_LIVING_DOCS=true` environment variable (see workflow env bindings).
- Output location defaults to `docs/diffs/PR_<number>.md`.
- Set `COMMIT_LIVING_DOCS=true` to auto-commit/push generated docs during the workflow run.

### Testing
Run unit tests locally:
```bash
pytest
```

### Install in Other Repositories
1. Publish or reference the package (see `docs/publishing.md` for options).
2. In the consuming repository’s workflow:
   ```yaml
   - name: Install DiffScribe
     run: pip install git+https://github.com/your-org/diffscribe.git@v0.1.0
   - name: Run DiffScribe
     env:
       OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
       GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
     run: python -m diffscribe.cli --event-path "$GITHUB_EVENT_PATH" --update-description
   ```
3. Optionally expose the CLI locally:
   ```bash
   pip install git+https://github.com/your-org/diffscribe.git@v0.1.0
   diffscribe --event-path path/to/event.json --output artifacts/pr_snapshot.json
   ```

### Roadmap Ideas
- Expand language coverage via Tree-sitter.
- Deeper risk heuristics and code ownership signals.
- Surface summaries in Slack/Teams or dashboards.

