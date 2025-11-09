from __future__ import annotations

import datetime
import subprocess
from pathlib import Path
from typing import List, Optional, Set

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
            "# Diffscribe PR Assistant",
            "────────────────────────────",
            f"PR #{pr_info.number} — {pr_info.title}",
            "",
            f"- Author: {pr_info.author}",
            f"- Base → Head: {pr_info.base_branch} ← {pr_info.head_branch}",
            f"- URL: {pr_info.url}",
            f"- Generated: {timestamp}",
            "",
        ]

        purpose = ai_summary.summary.strip(
        ) if ai_summary and ai_summary.summary else pr_info.body or "Purpose unavailable."
        lines.append("## 🧩 Purpose")
        lines.append("")
        lines.append(purpose.strip())
        lines.append("")

        lines.extend(
            self._build_section(
                "⚙️ Changes",
                ai_summary.behavior_changes if ai_summary else None,
                analysis,
                include_fallback=True,
            )
        )
        lines.extend(self._build_section(
            "⚠️ Risks", self._collect_risks(analysis), analysis))
        lines.extend(
            self._build_section("✅ Suggested Actions",
                                self._collect_actions(analysis), analysis)
        )

        return "\n".join(lines).strip() + "\n"

    def _build_section(
        self,
        title: str,
        ai_items: Optional[List[str]],
        analysis: AnalysisOutput,
        include_fallback: bool = False,
    ) -> List[str]:
        items: List[str] = []
        seen: Set[str] = set()

        if ai_items:
            for item in ai_items:
                text = item.strip()
                if text and text not in seen:
                    items.append(text)
                    seen.add(text)

        if include_fallback and not items:
            fallback = []
            for file in analysis.parsed_diff.files:
                for change in file.function_changes:
                    formatted = self._format_function_behavior(
                        file.filename, change)
                    if formatted not in fallback:
                        fallback.append(formatted)
            items.extend(fallback)

        cleaned = [item.strip() for item in items if item.strip()]
        if not cleaned:
            return []
        section_lines = [f"## {title}", ""]
        section_lines.extend(f"- {item}" for item in cleaned)
        section_lines.append("")
        return section_lines

    def _collect_risks(self, analysis: AnalysisOutput) -> List[str]:
        risks: List[str] = []
        ai_summary = analysis.ai_summary
        risk_assessment = analysis.risk_assessment

        if ai_summary and ai_summary.risks:
            for risk in ai_summary.risks:
                text = risk.strip()
                if text:
                    risks.append(text)

        if risk_assessment:
            if risk_assessment.high_risk_files:
                risks.append(
                    f"High-risk files modified: {', '.join(risk_assessment.high_risk_files)}")
            if risk_assessment.missing_tests:
                risks.append("Missing related tests covering modified code.")
            for api in risk_assessment.deprecated_apis:
                risks.append(f"Deprecated API usage: {api}")
            for note in risk_assessment.notes:
                risks.append(note)
        return risks

    def _collect_actions(self, analysis: AnalysisOutput) -> List[str]:
        actions: List[str] = []
        ai_summary = analysis.ai_summary
        risk_assessment = analysis.risk_assessment

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
            actions.extend(filtered)

        if risk_assessment:
            if risk_assessment.missing_tests and not any("unit test" in action.lower() for action in actions):
                actions.append(
                    "Add unit tests covering the modified functions.")
            if risk_assessment.deprecated_apis and not any("deprecated" in action.lower() for action in actions):
                actions.append(
                    "Replace or refactor deprecated API usage highlighted above.")
            if risk_assessment.high_risk_files and not any("review" in action.lower() for action in actions):
                actions.append(
                    "Perform a focused review of the high-risk modules that changed.")

        docs = []
        if ai_summary and ai_summary.suggested_actions:
            for action in ai_summary.suggested_actions:
                text = action.strip()
                if text.lower().startswith("docs:"):
                    docs.append(text.split(":", 1)[1].strip())
        if docs:
            actions.extend(docs)

        return actions

    def _format_function_behavior(self, filename: str, change: FunctionChange) -> str:
        function_name = "module-level logic" if change.name == "<module>" else change.name
        verb_map = {
            "added": "Added",
            "removed": "Removed",
            "modified": "Updated",
            "renamed": "Renamed",
        }
        verb = verb_map.get(change.change_type, "Updated")

        if change.change_type == "renamed" and change.previous_name:
            detail = f"{verb} `{change.previous_name}` to `{function_name}` in `{filename}`"
        else:
            detail = f"{verb} `{function_name}` in `{filename}`"

        return detail


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
