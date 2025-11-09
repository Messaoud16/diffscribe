from __future__ import annotations

import logging
import re
from typing import Dict, Literal

from ..models import (
    FunctionChange,
    ParsedDiff,
    ParsedFileDiff,
    PullRequestFile,
    PullRequestInfo,
)
from .language import detect_language

logger = logging.getLogger(__name__)

MODULE_SCOPE = "<module>"

PYTHON_DEF_PATTERN = re.compile(r"^\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")
PYTHON_CONTEXT_PATTERN = re.compile(r"(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")

JS_FUNCTION_PATTERN = re.compile(
    r"""
    ^
    \s*
    (?:
        function\s+([A-Za-z_$][\w$]*) |
        ([A-Za-z_$][\w$]*)\s*=\s*function |
        ([A-Za-z_$][\w$]*)\s*=\s*\([^)]*\)\s*=> |
        ([A-Za-z_$][\w$]*)\s*\(
    )
    """,
    re.VERBOSE,
)
JS_CONTEXT_PATTERN = re.compile(r"([A-Za-z_$][\w$]*)\s*\(")


class DiffParser:
    SUPPORTED_LANGUAGES = {"python", "javascript", "typescript"}

    def parse_pull_request(self, pull_request: PullRequestInfo) -> ParsedDiff:
        parsed_files = []
        for pr_file in pull_request.files:
            parsed = self._parse_file(pr_file)
            if parsed:
                parsed_files.append(parsed)
        return ParsedDiff(pull_request=pull_request, files=parsed_files)

    def _parse_file(self, file: PullRequestFile) -> ParsedFileDiff | None:
        language = detect_language(file.filename)
        if language not in self.SUPPORTED_LANGUAGES:
            language = language or "unknown"

        if not file.patch:
            logger.warning("No patch available for %s; skipping diff parsing.", file.filename)
            return ParsedFileDiff(
                filename=file.filename,
                language=language,
                status=file.status,
                previous_filename=file.previous_filename,
                additions=file.additions,
                deletions=file.deletions,
                summary="Diff unavailable; file too large or binary.",
                function_changes=[],
            )

        if language == "unknown":
            return ParsedFileDiff(
                filename=file.filename,
                language=language,
                status=file.status,
                previous_filename=file.previous_filename,
                additions=file.additions,
                deletions=file.deletions,
                summary="Unsupported language; listing file-level changes only.",
                function_changes=[],
            )

        function_stats: Dict[str, Dict[str, int | bool]] = {}
        current_scope = MODULE_SCOPE
        renamed_pairs: Dict[str, str] = {}
        pending_removed: list[str] = []

        for line in file.patch.splitlines():
            if line.startswith("@@"):
                context_name = self._extract_context_name(line, language)
                current_scope = context_name or MODULE_SCOPE
                self._ensure_scope(function_stats, current_scope)
                continue

            if not line or line[0] not in {"+", "-"}:
                continue

            sign = line[0]
            content = line[1:]

            detected_scope = self._detect_definition_scope(content, language)
            if detected_scope:
                if sign == "-":
                    pending_removed.append(detected_scope)
                current_scope = detected_scope
                self._ensure_scope(function_stats, current_scope)
                if sign == "+":
                    function_stats[current_scope]["definition_added"] = True
                    if pending_removed:
                        previous_name = pending_removed.pop(0)
                        if previous_name != detected_scope:
                            renamed_pairs[detected_scope] = previous_name
                            if previous_name in function_stats:
                                old_stats = function_stats.pop(previous_name)
                                self._ensure_scope(function_stats, detected_scope)
                                new_stats = function_stats[detected_scope]
                                new_stats["lines_removed"] += int(
                                    old_stats.get("lines_removed", 0)
                                )
                                new_stats["definition_removed"] = (
                                    bool(new_stats["definition_removed"])
                                    or bool(old_stats.get("definition_removed"))
                                )
                elif sign == "-":
                    function_stats[current_scope]["definition_removed"] = True

            self._ensure_scope(function_stats, current_scope)
            if sign == "+":
                function_stats[current_scope]["lines_added"] += 1
            elif sign == "-":
                function_stats[current_scope]["lines_removed"] += 1

        function_changes = [
            self._build_function_change(
                scope,
                stats,
                previous_name=renamed_pairs.get(scope),
            )
            for scope, stats in function_stats.items()
        ]
        summary = self._summarize_file(
            function_changes, language, file.status, file.previous_filename
        )

        return ParsedFileDiff(
            filename=file.filename,
            language=language,
            status=file.status,
            previous_filename=file.previous_filename,
            additions=file.additions,
            deletions=file.deletions,
            function_changes=function_changes,
            summary=summary,
        )

    def _ensure_scope(self, store: Dict[str, Dict[str, int | bool]], scope: str) -> None:
        if scope not in store:
            store[scope] = {
                "lines_added": 0,
                "lines_removed": 0,
                "definition_added": False,
                "definition_removed": False,
            }

    def _extract_context_name(self, line: str, language: str) -> str | None:
        context = line.split("@@")[-1]
        if language == "python":
            match = PYTHON_CONTEXT_PATTERN.search(context)
            if match:
                return match.group(1)
        elif language in {"javascript", "typescript"}:
            match = JS_CONTEXT_PATTERN.search(context)
            if match:
                return match.group(1)
        return None

    def _detect_definition_scope(self, content: str, language: str) -> str | None:
        if language == "python":
            match = PYTHON_DEF_PATTERN.match(content)
            if match:
                return match.group(1)
        elif language in {"javascript", "typescript"}:
            normalized = content.strip()
            prefixes = [
                "export default",
                "export",
                "async",
                "const",
                "let",
                "var",
            ]
            for prefix in prefixes:
                if normalized.startswith(prefix + " "):
                    normalized = normalized[len(prefix) :].lstrip()
            match = JS_FUNCTION_PATTERN.match(normalized)
            if match:
                for group in match.groups():
                    if group:
                        return group
        return None

    def _build_function_change(
        self,
        scope: str,
        stats: Dict[str, int | bool],
        previous_name: str | None = None,
    ) -> FunctionChange:
        change_type: Literal["added", "modified", "removed", "renamed"]
        lines_added = int(stats["lines_added"])
        lines_removed = int(stats["lines_removed"])
        definition_added = bool(stats["definition_added"])
        definition_removed = bool(stats["definition_removed"])

        if previous_name and previous_name != scope:
            change_type = "renamed"
        elif definition_added and not definition_removed and lines_removed == 0:
            change_type = "added"
        elif definition_removed and not definition_added and lines_added == 0:
            change_type = "removed"
        else:
            change_type = "modified"

        summary = self._summarize_scope(
            scope,
            change_type,
            lines_added,
            lines_removed,
            previous_name=previous_name,
        )
        return FunctionChange(
            name=scope,
            change_type=change_type,
            lines_added=lines_added,
            lines_removed=lines_removed,
            summary=summary,
            previous_name=previous_name,
        )

    def _summarize_scope(
        self,
        scope: str,
        change_type: str,
        added: int,
        removed: int,
        previous_name: str | None = None,
    ) -> str:
        if scope == MODULE_SCOPE:
            scope_desc = "module-level logic"
        else:
            scope_desc = f"{scope}()"

        if change_type == "renamed" and previous_name:
            return f"Renamed {previous_name}() -> {scope}() (+{added} / -{removed} lines)"
        if change_type == "added":
            return f"Added {scope_desc} (+{added} lines)"
        if change_type == "removed":
            return f"Removed {scope_desc} (-{removed} lines)"
        return f"Modified {scope_desc} (+{added} / -{removed} lines)"

    def _summarize_file(
        self,
        function_changes: list[FunctionChange],
        language: str,
        status: str,
        previous_filename: str | None,
    ) -> str:
        if not function_changes:
            return f"Updated {language} file without detectable function-level changes."

        added = sum(1 for fc in function_changes if fc.change_type == "added")
        removed = sum(1 for fc in function_changes if fc.change_type == "removed")
        modified = sum(1 for fc in function_changes if fc.change_type == "modified")
        renamed = sum(1 for fc in function_changes if fc.change_type == "renamed")

        parts = []
        if added:
            parts.append(f"{added} added")
        if removed:
            parts.append(f"{removed} removed")
        if modified:
            parts.append(f"{modified} modified")
        if renamed:
            parts.append(f"{renamed} renamed")
        detail = ", ".join(parts)

        if status == "renamed" and previous_filename:
            return f"Renamed file from {previous_filename} and detected {detail} function-level changes."

        return f"Detected {detail} function-level changes."
