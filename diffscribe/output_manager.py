from __future__ import annotations

from textwrap import dedent
from typing import List, Set

from .models import AnalysisOutput, AISummary, RiskAssessment, FunctionChange

COMMENT_MARKER = "<!-- DiffScribe -->"


class CommentFormatter:
    def render(self, analysis: AnalysisOutput, include_all_functions: bool = False) -> str:
        sections: List[str] = []
        pr = analysis.parsed_diff.pull_request

        header = [
            "Diffscribe PR Assistant",
            "────────────────────────────",
            f"PR #{pr.number} — {pr.title or 'Untitled'}",
            "",
        ]
        sections.append("\n".join(header))

        purpose = self._determine_purpose(analysis)
        sections.append(self._build_section("🧩 Purpose", [purpose]))

        changes = self._collect_changes(analysis, include_all_functions)
        if changes:
            sections.append(self._build_section("⚙️ Changes", changes))

        risks = self._collect_risks(analysis)
        if risks:
            sections.append(self._build_section("⚠️ Risks", risks))

        actions = self._collect_actions(analysis)
        if actions:
            sections.append(self._build_section(
                "✅ Suggested Actions", actions))

        docs = self._collect_docs(analysis)
        if docs:
            sections.append(self._build_section("📂 Docs Updated", docs))

        reviewers = self._collect_reviewers(analysis)
        if reviewers:
            sections.append(self._build_section("🔗 Reviewers", reviewers))

        body = "\n".join(section for section in sections if section)
        return dedent(body).strip()

    def _determine_purpose(self, analysis: AnalysisOutput) -> str:
        if analysis.ai_summary and analysis.ai_summary.summary:
            return analysis.ai_summary.summary.strip()
        pr = analysis.parsed_diff.pull_request
        if pr.body:
            return pr.body.strip().splitlines()[0]
        return "Purpose unavailable."

    def _build_section(self, title: str, items: List[str]) -> str:
        cleaned = [item.strip() for item in items if item and item.strip()]
        if not cleaned:
            return ""
        bullet_lines = "\n".join(f"- {item}" for item in cleaned)
        return f"{title}\n\n{bullet_lines}\n"

    def _collect_changes(self, analysis: AnalysisOutput, include_all_functions: bool) -> List[str]:
        seen: Set[str] = set()
        changes: List[str] = []
        ai_summary = analysis.ai_summary

        if ai_summary and ai_summary.behavior_changes:
            for change in ai_summary.behavior_changes:
                text = change.strip()
                if text and text not in seen:
                    changes.append(text)
                    seen.add(text)

        return changes

    def _collect_risks(self, analysis: AnalysisOutput) -> List[str]:
        risks: List[str] = []
        ai_summary = analysis.ai_summary
        risk_assessment = analysis.risk_assessment

        if ai_summary and ai_summary.risks:
            for item in ai_summary.risks:
                text = item.strip()
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

    def _collect_docs(self, analysis: AnalysisOutput) -> List[str]:
        docs: List[str] = []
        for file_diff in analysis.parsed_diff.files:
            if file_diff.filename.startswith("docs/"):
                docs.append(file_diff.filename)

        ai_summary = analysis.ai_summary
        if ai_summary and ai_summary.suggested_actions:
            for action in ai_summary.suggested_actions:
                text = action.strip()
                if text.lower().startswith("docs:"):
                    docs.append(text.split(":", 1)[1].strip())
        return docs

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

        return actions

    def _collect_reviewers(self, analysis: AnalysisOutput) -> List[str]:
        reviewers: List[str] = []
        pr = analysis.parsed_diff.pull_request
        teams = [label for label in pr.labels if label.endswith("-team")]
        if teams:
            reviewers.append(", ".join(f"@{team}" for team in teams))
        return reviewers

    def _format_function_behavior(self, filename: str, change: FunctionChange) -> str:
        name = "module-level logic" if change.name == "<module>" else change.name
        verb_map = {
            "added": "Added",
            "removed": "Removed",
            "modified": "Updated",
            "renamed": "Renamed",
        }
        verb = verb_map.get(change.change_type, "Updated")

        if change.change_type == "renamed" and getattr(change, "previous_name", None):
            return f"{name} — renamed from {change.previous_name}"
        if change.summary:
            return change.summary.replace("()", "").strip()
        return f"{name} — {verb.lower()} in {filename}"
