from __future__ import annotations

from textwrap import dedent
from typing import List

from .models import AnalysisOutput, AISummary, RiskAssessment

COMMENT_MARKER = "<!-- DiffScribe -->"


class CommentFormatter:
    def render(self, analysis: AnalysisOutput) -> str:
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

        if ai_summary and ai_summary.model:
            lines.append("")
            lines.append(f"_Generated with {ai_summary.model}_")

        body = "\n".join(lines).strip()
        return dedent(body).strip()
