from diffscribe.models import (
    AISummary,
    AnalysisOutput,
    ParsedDiff,
    ParsedFileDiff,
    PullRequestInfo,
    RiskAssessment,
)
from diffscribe.output_manager import CommentFormatter


def build_pr() -> PullRequestInfo:
    return PullRequestInfo(
        number=42,
        title="Demo",
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


def test_comment_formatter_includes_sections():
    parsed = ParsedDiff(
        pull_request=build_pr(),
        files=[
            ParsedFileDiff(
                filename="src/app.py",
                language="python",
                status="modified",
                additions=5,
                deletions=1,
                summary="Detected 1 modified function-level changes.",
                function_changes=[],
            )
        ],
    )
    ai_summary = AISummary(
        summary="Updates app logic.",
        behavior_changes=["App returns JSON."],
        risks=["Needs extra tests."],
        suggested_actions=["Add integration test."],
        model="gpt-4o-mini",
    )
    risks = RiskAssessment(high_risk_files=["core/app.py"], missing_tests=True)

    formatter = CommentFormatter()
    body = formatter.render(AnalysisOutput(parsed_diff=parsed, ai_summary=ai_summary, risk_assessment=risks))

    assert "DiffScribe Summary" in body
    assert "Behavior Changes" in body
    assert "Risks & Flags" in body
    assert "Suggested Actions" in body
    assert "gpt-4o-mini" in body

