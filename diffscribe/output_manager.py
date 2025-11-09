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
                text = change.strip()
                if not text:
                    continue
                if text not in behavior_items:
                    behavior_items.append(text)
        fallback_items: List[str] = []
        for file_diff in analysis.parsed_diff.files:
            for change in file_diff.function_changes:
                formatted = self._format_function_behavior(
                    file_diff.filename, change)
                if formatted not in fallback_items:
                    fallback_items.append(formatted)

        if include_all_functions or not behavior_items:
            behavior_items.extend(fallback_items)
        if behavior_items:
            lines.append("")
            lines.append("**Behavior Changes**")
            for item in behavior_items:
                bullet = item.strip()
                if not bullet:
                    continue
                if not bullet.startswith("-"):
                    bullet = f"- {bullet}"
                lines.append(bullet)

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

        if risk_assessment:
            if risk_assessment.missing_tests and not any(
                "unit test" in action.lower() for action in suggested_actions
            ):
                suggested_actions.append(
                    "Add unit tests covering the modified functions."
                )
            if risk_assessment.deprecated_apis and not any(
                "deprecated" in action.lower() for action in suggested_actions
            ):
                suggested_actions.append(
                    "Replace or refactor deprecated API usage highlighted above."
                )
            if risk_assessment.high_risk_files and not any(
                "review" in action.lower() for action in suggested_actions
            ):
                suggested_actions.append(
                    "Perform a focused review of the high-risk modules that changed."
                )

        if suggested_actions:
            lines.append("")
            lines.append("**Suggested Actions**")
            for item in suggested_actions:
                lines.append(f"- {item}")

        body = "\n".join(lines).strip()
        return dedent(body).strip()

    def _format_function_behavior(self, filename: str, change: FunctionChange) -> str:
        function_name = "module-level logic" if change.name == "<module>" else change.name
        verb_map = {
            "added": "Added",
            "removed": "Removed",
            "modified": "Updated",
            "renamed": "Renamed",
        }
        verb = verb_map.get(change.change_type, "Updated")

        if change.change_type == "renamed" and getattr(change, "previous_name", None):
            detail = f"{verb} `{change.previous_name}` to `{function_name}` in `{filename}`"
        else:
            detail = f"{verb} `{function_name}` in `{filename}`"

        return detail
