from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

from .models import ParsedDiff, PullRequestInfo, RiskAssessment, PullRequestFile

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    high_risk_paths: List[str]
    test_indicators: List[str]
    deprecated_identifiers_python: List[str]
    deprecated_identifiers_js: List[str]

    @classmethod
    def default(cls) -> "RiskConfig":
        return cls(
            high_risk_paths=["core/", "shared/", "infra/", "services/"],
            test_indicators=["tests/", "__tests__/", "test_", "_test.py"],
            deprecated_identifiers_python=[
                "logging.warn", "asyncio.get_event_loop"],
            deprecated_identifiers_js=["componentWillMount", "$http"],
        )


class RiskAnalyzer:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig.default()

    def assess(self, pr_info: PullRequestInfo, parsed_diff: ParsedDiff) -> RiskAssessment:
        high_risk_files = self._detect_high_risk_files(pr_info.files)
        missing_tests = self._detect_missing_tests(pr_info.files)
        deprecated_apis = self._detect_deprecated_apis(pr_info.files)
        notes: List[str] = []

        if pr_info.draft:
            notes.append(
                "PR marked as draft; reviewers may defer until ready.")

        if pr_info.is_mergeable is False:
            notes.append(
                "GitHub reports merge conflicts that must be resolved.")

        return RiskAssessment(
            high_risk_files=high_risk_files,
            missing_tests=missing_tests,
            deprecated_apis=deprecated_apis,
            notes=notes,
        )

    def _detect_high_risk_files(self, files: Iterable[PullRequestFile]) -> List[str]:
        risky = []
        for file in files:
            filename = file.filename
            if any(marker in filename for marker in self.config.high_risk_paths):
                risky.append(filename)
        return risky

    def _detect_missing_tests(self, files: Iterable[PullRequestFile]) -> bool:
        code_files = [file for file in files if file.filename.endswith(
            (".py", ".js", ".jsx"))]
        if not code_files:
            return False

        test_files = [
            file
            for file in files
            if any(indicator in file.filename for indicator in self.config.test_indicators)
        ]
        return len(test_files) == 0

    def _detect_deprecated_apis(self, files: Iterable[PullRequestFile]) -> List[str]:
        issues: List[str] = []
        for file in files:
            if not file.patch:
                continue
            identifiers = []
            if file.filename.endswith(".py"):
                identifiers = self.config.deprecated_identifiers_python
            elif file.filename.endswith((".js", ".jsx")):
                identifiers = self.config.deprecated_identifiers_js
            else:
                continue

            for identifier in identifiers:
                if identifier in file.patch:
                    issues.append(f"{identifier} in {file.filename}")
        return issues
