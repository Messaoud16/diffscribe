from __future__ import annotations

import datetime
import subprocess
from pathlib import Path
from typing import Optional

from .models import AnalysisOutput, PullRequestInfo, FunctionChange


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

        behavior_items = []
        if ai_summary and ai_summary.behavior_changes:
            for change in ai_summary.behavior_changes:
                bullet = f"- {change}"
                if bullet not in behavior_items:
                    behavior_items.append(bullet)
        for file in analysis.parsed_diff.files:
            for change in file.function_changes:
                formatted = self._format_function_behavior(
                    file.filename, change)
                if formatted not in behavior_items:
                    behavior_items.append(formatted)
        if behavior_items:
            lines.append("## Modified Methods / Classes")
            lines.append("")
            for item in behavior_items:
                lines.append(item)
            lines.append("")

        if risk and (risk.high_risk_files or risk.missing_tests or risk.deprecated_apis or risk.notes):
            lines.append("## Risks & Potential Issues")
            lines.append("")
            if risk.high_risk_files:
                lines.append(
                    f"- High-risk files modified: {', '.join(risk.high_risk_files)}")
            if risk.missing_tests:
                lines.append("- Missing related tests covering modified code.")
            for item in risk.deprecated_apis:
                lines.append(f"- Deprecated API: {item}")
            for note in risk.notes:
                lines.append(f"- {note}")
            lines.append("")

        suggested_actions = []
        if ai_summary and ai_summary.suggested_actions:
            filtered = [
                action.strip()
                for action in ai_summary.suggested_actions
                if action
                and action.strip().lower()
                not in {
                    "check for any potential security vulnerabilities introduced by new changes",
                    "verify that all modified functions maintain expected behavior",
                    "review the new server functionality and ensure it meets requirements",
                }
            ]
            suggested_actions.extend(filtered)

        if risk:
            if risk.missing_tests and not any("unit test" in action.lower() for action in suggested_actions):
                suggested_actions.append(
                    "Add unit tests covering the modified functions.")
            if risk.deprecated_apis and not any("deprecated" in action.lower() for action in suggested_actions):
                suggested_actions.append(
                    "Replace or refactor deprecated API usage highlighted above.")
            if risk.high_risk_files and not any("review" in action.lower() for action in suggested_actions):
                suggested_actions.append(
                    "Perform a focused review of the high-risk modules that changed.")

        if suggested_actions:
            lines.append("## Suggested Actions")
            lines.append("")
            for item in suggested_actions:
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
                        lines.append(
                            f"- {self._format_function_behavior(file.filename, change)}")
                lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _format_function_behavior(self, filename: str, change: FunctionChange) -> str:
        function_name = "module-level logic" if change.name == "<module>" else change.name
        if change.change_type == "renamed" and change.previous_name:
            detail = f"Renamed `{change.previous_name}` to `{function_name}` in `{filename}`"
        else:
            detail = f"{change.change_type.title()} `{function_name}` in `{filename}`"

        line_delta = ""
        if change.lines_added or change.lines_removed:
            line_delta = f" (+{change.lines_added}/-{change.lines_removed} lines)"

        summary = change.summary or ""
        summary = summary.replace("()", "")
        summary_detail = f" — {summary}" if summary else ""

        return f"- `{filename}` · {detail}{line_delta}{summary_detail}"


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
