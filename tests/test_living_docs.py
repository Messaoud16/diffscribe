from pathlib import Path

from diffscribe.living_docs import LivingDocsGenerator
from diffscribe.models import (
    AISummary,
    AnalysisOutput,
    FunctionChange,
    ParsedDiff,
    ParsedFileDiff,
    PullRequestInfo,
    RiskAssessment,
)


def build_pr() -> PullRequestInfo:
    return PullRequestInfo(
        number=99,
        title="Docs test",
        body="",
        author="tester",
        url="http://example.com",
        base_branch="main",
        head_branch="feature",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        files=[],
        labels=[],
        draft=False,
        is_mergeable=True,
    )


def test_living_doc_generation(tmp_path: Path):
    parsed = ParsedDiff(
        pull_request=build_pr(),
        files=[
            ParsedFileDiff(
                filename="src/file.py",
                language="python",
                status="modified",
                additions=3,
                deletions=1,
                summary="Detected 1 modified function-level changes.",
                function_changes=[
                    FunctionChange(
                        name="helper",
                        change_type="modified",
                        lines_added=3,
                        lines_removed=1,
                        summary="Modified helper (+3 / -1 lines)",
                    )
                ],
            )
        ],
    )
    ai_summary = AISummary(
        summary="Summary text.",
        behavior_changes=["Behavior change"],
        risks=[],
        suggested_actions=[],
    )
    analysis = AnalysisOutput(parsed_diff=parsed, ai_summary=ai_summary, risk_assessment=RiskAssessment())
    generator = LivingDocsGenerator(tmp_path / "docs" / "diffs")

    doc_path = generator.generate(parsed.pull_request, analysis)

    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")
    assert "Summary text." in content
    assert "Diffscribe PR Assistant" in content
    assert "🧩 Purpose" in content
    assert "- Behavior change" in content

