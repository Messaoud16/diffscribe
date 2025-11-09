from __future__ import annotations

from textwrap import dedent
from typing import List

from .models import AnalysisOutput, AISummary, RiskAssessment, FunctionChange

COMMENT_MARKER = "<!-- DiffScribe -->"


class CommentFormatter:
    def render(self, analysis: AnalysisOutput, include_all_functions: bool = False) -> str:
        lines: List[str] = []
        lines.append("## DiffScribe Summary")

        ai_summary: AISummary | None = analysis.ai_summary
        risk_assessment: RiskAssessment | None = analysis.risk_assessment

        summary_text = ai_summary.summary if ai_summary and ai_summary.summary else "Summary unavailable."
        lines.append("")
        lines.append(summary_text.strip())

        behavior_items: List[str] = []
        if ai_summary and ai_summary.behavior_changes:
            for change in ai_summary.behavior_changes:
                bullet = f"- {change}"
                if bullet not in behavior_items:
                    behavior_items.append(bullet)
        for file_diff in analysis.parsed_diff.files:
            for change in file_diff.function_changes:
                formatted = self._format_function_behavior(
                    file_diff.filename, change)
                if include_all_functions or formatted not in behavior_items:
                    behavior_items.append(formatted)
        if behavior_items:
            lines.append("")
            lines.append("**Modified Methods / Classes**")
            for item in behavior_items:
                lines.append(item)

        risk_items = []
        if ai_summary and ai_summary.risks:
            risk_items.extend(ai_summary.risks)
        if risk_assessment:
            if risk_assessment.high_risk_files:
                joined = ", ".join(risk_assessment.high_risk_files)
                risk_items.append(f"High-risk files modified: {joined}")
            if risk_assessment.missing_tests:
                risk_items.append(
                    "Missing related tests covering modified code.")
            if risk_assessment.deprecated_apis:
                risk_items.extend(
                    f"Deprecated API usage: {item}" for item in risk_assessment.deprecated_apis)
            for note in risk_assessment.notes:
                risk_items.append(note)

        if risk_items:
            lines.append("")
            lines.append("**Risks & Potential Issues**")
            for item in risk_items:
                lines.append(f"- {item}")

        suggested_actions: List[str] = []
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

        if risk_assessment and risk_assessment.missing_tests:
            if not any("unit test" in action.lower() for action in suggested_actions):
                suggested_actions.append(
                    "Add unit tests covering the modified functions.")

        if suggested_actions:
            lines.append("")
            lines.append("**Suggested Actions**")
            for item in suggested_actions:
                lines.append(f"- {item}")

        body = "\n".join(lines).strip()
        return dedent(body).strip()

    def _format_function_behavior(self, filename: str, change: FunctionChange) -> str:
        function_name = "module-level logic" if change.name == "<module>" else change.name
        if change.change_type == "renamed" and getattr(change, "previous_name", None):
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
