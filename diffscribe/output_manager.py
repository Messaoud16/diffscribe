from __future__ import annotations

from textwrap import dedent
from typing import List

from .models import AnalysisOutput, FunctionChange

COMMENT_MARKER = "<!-- DiffScribe -->"


class CommentFormatter:
    def render(
        self,
        analysis: AnalysisOutput,
        include_function_changes: bool = False,
    ) -> str:
        pr = analysis.parsed_diff.pull_request
        header = f'### 🤖 Diffscribe Summary — PR #{pr.number} "{pr.title or "Untitled"}"\n'
        sections: List[str] = [header]

        sections.extend(self._format_goal(self._extract_goal(analysis)))

        changes = self._extract_changes(analysis, include_function_changes)
        if changes:
            sections.extend(self._format_section("🧩 What Changed", changes))

        risks = self._extract_risks(analysis)
        if risks:
            sections.extend(self._format_section("⚠️ Risks", risks))

        actions = self._extract_actions(analysis)
        if actions:
            sections.extend(self._format_section(
                "🧪 Suggested Actions", actions))

        body = "\n".join(part for part in sections if part)
        return dedent(body).strip()

    def _extract_goal(self, analysis: AnalysisOutput) -> str:
        if analysis.ai_summary and analysis.ai_summary.summary:
            return analysis.ai_summary.summary.strip()
        pr = analysis.parsed_diff.pull_request
        if pr.body:
            return pr.body.strip().splitlines()[0]
        return "Purpose unavailable."

    def _extract_changes(
        self,
        analysis: AnalysisOutput,
        include_fallback: bool,
    ) -> List[str]:
        changes: List[str] = []
        if analysis.ai_summary and analysis.ai_summary.behavior_changes:
            changes.extend(
                item.strip()
                for item in analysis.ai_summary.behavior_changes
                if item and item.strip()
            )
        if include_fallback and not changes:
            for file_diff in analysis.parsed_diff.files:
                for change in file_diff.function_changes:
                    changes.append(self._format_function_behavior(
                        file_diff.filename, change))
        return changes

    def _extract_risks(self, analysis: AnalysisOutput) -> List[str]:
        risks: List[str] = []
        if analysis.ai_summary and analysis.ai_summary.risks:
            risks.extend(
                item.strip() for item in analysis.ai_summary.risks if item and item.strip()
            )

        risk_assessment = analysis.risk_assessment
        if risk_assessment:
            if risk_assessment.high_risk_files:
                risks.append(
                    f"High-risk files modified: {', '.join(risk_assessment.high_risk_files)}"
                )
            if risk_assessment.missing_tests:
                risks.append("Missing related tests covering modified code.")
            for api in risk_assessment.deprecated_apis:
                risks.append(f"Deprecated API usage: {api}")
            for note in risk_assessment.notes:
                risks.append(note)
        return risks

    def _extract_actions(self, analysis: AnalysisOutput) -> List[str]:
        actions: List[str] = []
        if analysis.ai_summary and analysis.ai_summary.suggested_actions:
            actions.extend(
                item.strip()
                for item in analysis.ai_summary.suggested_actions
                if item and item.strip()
            )

        risk_assessment = analysis.risk_assessment
        if risk_assessment:
            if risk_assessment.missing_tests and not any(
                "unit test" in action.lower() for action in actions
            ):
                actions.append(
                    "Add unit tests covering the modified functions.")
            if risk_assessment.deprecated_apis and not any(
                "deprecated" in action.lower() for action in actions
            ):
                actions.append(
                    "Replace or refactor deprecated API usage highlighted above.")
            if risk_assessment.high_risk_files and not any(
                "review" in action.lower() for action in actions
            ):
                actions.append(
                    "Perform a focused review of the high-risk modules that changed.")
        return actions

    def _format_goal(self, goal: str) -> List[str]:
        return [
            "**🎯 Goal**  ",
            goal if goal else "Purpose unavailable.",
            "",
        ]

    def _format_section(self, title: str, items: List[str]) -> List[str]:
        cleaned = [item for item in items if item]
        if not cleaned:
            return []
        lines = [f"**{title}**  "]
        lines.extend(f"- {item}" for item in cleaned)
        lines.append("")
        return lines

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
            return f"{function_name} — renamed from {change.previous_name}"
        if change.summary:
            return change.summary.replace("()", "").strip()
        return f"{function_name} — {verb.lower()} in {filename}"
