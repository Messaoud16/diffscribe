from __future__ import annotations

import datetime
import subprocess
from pathlib import Path
from typing import Optional

from .models import AnalysisOutput, PullRequestInfo


class LivingDocsGenerator:
    def __init__(self, docs_dir: Path) -> None:
        self.docs_dir = docs_dir

    def generate(self, pr_info: PullRequestInfo, analysis: AnalysisOutput) -> Path:
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        path = self.docs_dir / f"PR_{pr_info.number}.md"
        content = self._render(pr_info, analysis)
        path.write_text(content, encoding="utf-8")
        return path

    def _render(self, pr_info: PullRequestInfo, analysis: AnalysisOutput) -> str:
        ai_summary = analysis.ai_summary
        risk = analysis.risk_assessment
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()

        lines = [
            f"# PR #{pr_info.number}: {pr_info.title}",
            "",
            f"- Author: {pr_info.author}",
            f"- Base → Head: {pr_info.base_branch} ← {pr_info.head_branch}",
            f"- URL: {pr_info.url}",
            f"- Generated: {timestamp}",
            "",
        ]

        if ai_summary and ai_summary.summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(ai_summary.summary.strip())
            lines.append("")

        if ai_summary and ai_summary.behavior_changes:
            lines.append("## Behavior Changes")
            lines.append("")
            for item in ai_summary.behavior_changes:
                lines.append(f"- {item}")
            lines.append("")

        if risk and (risk.high_risk_files or risk.missing_tests or risk.deprecated_apis or risk.notes):
            lines.append("## Risks & Flags")
            lines.append("")
            if risk.high_risk_files:
                lines.append(
                    f"- High-risk files: {', '.join(risk.high_risk_files)}")
            if risk.missing_tests:
                lines.append("- Missing related tests for code changes.")
            for item in risk.deprecated_apis:
                lines.append(f"- Deprecated API: {item}")
            for note in risk.notes:
                lines.append(f"- {note}")
            lines.append("")

        if ai_summary and ai_summary.suggested_actions:
            lines.append("## Suggested Actions")
            lines.append("")
            for item in ai_summary.suggested_actions:
                lines.append(f"- {item}")
            lines.append("")

        if analysis.parsed_diff.files:
            lines.append("## Changed Files")
            lines.append("")
            for file in analysis.parsed_diff.files:
                lines.append(f"### {file.filename}")
                if file.summary:
                    lines.append(file.summary)
                if file.function_changes:
                    lines.append("")
                    lines.append("Function-level changes:")
                    for change in file.function_changes:
                        lines.append(f"- {change.summary}")
                lines.append("")

        return "\n".join(lines).strip() + "\n"


def commit_living_doc(
    path: Path,
    pr_number: int,
    author_name: str = "github-actions[bot]",
    author_email: str = "41898282+github-actions[bot]@users.noreply.github.com",
) -> None:
    subprocess.run(["git", "config", "--global",
                   "user.name", author_name], check=False)
    subprocess.run(["git", "config", "--global",
                   "user.email", author_email], check=False)
    subprocess.run(["git", "add", str(path)], check=False)
    result = subprocess.run(
        ["git", "commit", "-m", f"docs: update PR {pr_number} summary"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "nothing to commit" not in (result.stderr or "").lower():
        raise subprocess.CalledProcessError(
            result.returncode, result.args, output=result.stdout, stderr=result.stderr)
