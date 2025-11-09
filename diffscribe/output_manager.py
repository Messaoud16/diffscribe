from __future__ import annotations

from textwrap import dedent
from typing import List

from .models import AnalysisOutput, AISummary, RiskAssessment

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

        if ai_summary and ai_summary.behavior_changes:
            lines.append("")
            lines.append("**Behavior Changes**")
            for item in ai_summary.behavior_changes:
                lines.append(f"- {item}")

        function_items: List[str] = []
        for file_diff in analysis.parsed_diff.files:
            for change in file_diff.function_changes:
                change_name = (
                    "module-level logic" if change.name == "<module>" else change.name
                )
                if change.previous_name and change.previous_name != change.name:
                    change_details = f"{change.change_type} ({change.previous_name} -> {change.name})"
                else:
                    change_details = f"{change.change_type}"
                if change.lines_added or change.lines_removed:
                    change_details += f" (+{change.lines_added}/-{change.lines_removed})"
                function_items.append(
                    f"- `{file_diff.filename}` · `{change_name}` · {change_details}"
                )

        if include_all_functions or function_items:
            lines.append("")
            lines.append("**Function Changes**")
            if function_items:
                lines.extend(function_items)
            else:
                lines.append("- Detected no function-level changes.")

        risk_items = []
        if ai_summary and ai_summary.risks:
            risk_items.extend(ai_summary.risks)
        if risk_assessment:
            if risk_assessment.high_risk_files:
                joined = ", ".join(risk_assessment.high_risk_files)
                risk_items.append(f"High-risk files touched: {joined}")
            if risk_assessment.missing_tests:
                risk_items.append("Missing related tests for code changes.")
            if risk_assessment.deprecated_apis:
                risk_items.extend(
                    f"Deprecated API usage: {item}" for item in risk_assessment.deprecated_apis)
            for note in risk_assessment.notes:
                risk_items.append(note)

        if risk_items:
            lines.append("")
            lines.append("**Risks & Flags**")
            for item in risk_items:
                lines.append(f"- {item}")

        if ai_summary and ai_summary.suggested_actions:
            lines.append("")
            lines.append("**Suggested Actions**")
            for item in ai_summary.suggested_actions:
                lines.append(f"- {item}")

        body = "\n".join(lines).strip()
        return dedent(body).strip()
