from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from typing import Literal


@dataclass
class PullRequestFile:
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    sha: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PullRequestInfo:
    number: int
    title: str
    body: Optional[str]
    author: str
    url: str
    base_branch: str
    head_branch: str
    created_at: str
    updated_at: str
    files: List[PullRequestFile] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    draft: bool = False
    is_mergeable: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "author": self.author,
            "url": self.url,
            "base_branch": self.base_branch,
            "head_branch": self.head_branch,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": [file.to_dict() for file in self.files],
            "labels": self.labels,
            "draft": self.draft,
            "is_mergeable": self.is_mergeable,
        }


@dataclass
class FunctionChange:
    name: str
    change_type: Literal["added", "modified", "removed"]
    lines_added: int
    lines_removed: int
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedFileDiff:
    filename: str
    language: str
    status: str
    additions: int
    deletions: int
    function_changes: List[FunctionChange] = field(default_factory=list)
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "language": self.language,
            "status": self.status,
            "additions": self.additions,
            "deletions": self.deletions,
            "summary": self.summary,
            "function_changes": [fc.to_dict() for fc in self.function_changes],
        }


@dataclass
class ParsedDiff:
    pull_request: PullRequestInfo
    files: List[ParsedFileDiff] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pull_request": self.pull_request.to_dict(),
            "files": [file.to_dict() for file in self.files],
        }


@dataclass
class AISummary:
    summary: str
    behavior_changes: List[str]
    risks: List[str]
    suggested_actions: List[str]
    model: Optional[str] = None
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "behavior_changes": self.behavior_changes,
            "risks": self.risks,
            "suggested_actions": self.suggested_actions,
            "model": self.model,
            "raw_response": self.raw_response,
        }


@dataclass
class AnalysisOutput:
    parsed_diff: ParsedDiff
    ai_summary: Optional[AISummary] = None
    risk_assessment: Optional["RiskAssessment"] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parsed_diff": self.parsed_diff.to_dict(),
            "ai_summary": self.ai_summary.to_dict() if self.ai_summary else None,
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
        }


@dataclass
class RiskAssessment:
    high_risk_files: List[str] = field(default_factory=list)
    missing_tests: bool = False
    deprecated_apis: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "high_risk_files": self.high_risk_files,
            "missing_tests": self.missing_tests,
            "deprecated_apis": self.deprecated_apis,
            "notes": self.notes,
        }
