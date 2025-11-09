from __future__ import annotations

import datetime
import subprocess
from pathlib import Path

from .models import AnalysisOutput, PullRequestInfo
from .output_manager import CommentFormatter


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
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()

        formatter = CommentFormatter()
        summary_body = formatter.render(
            analysis,
            include_function_changes=True,
        )

        lines = [
            "# Diffscribe PR Assistant",
            f"PR #{pr_info.number} — {pr_info.title}",
            "",
            f"- Author: {pr_info.author}",
            f"- Base → Head: {pr_info.base_branch} ← {pr_info.head_branch}",
            f"- URL: {pr_info.url}",
            f"- Generated: {timestamp}",
            "",
            summary_body,
        ]

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
