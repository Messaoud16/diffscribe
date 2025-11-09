from diffscribe.models import (
    AISummary,
    AnalysisOutput,
    FunctionChange,
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
                function_changes=[
                    FunctionChange(
                        name="update_pr_body",
                        change_type="modified",
                        lines_added=5,
                        lines_removed=1,
                        summary="Modified update_pr_body (+5 / -1 lines)",
                    )
                ],
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

    assert "Diffscribe PR Assistant" in body
    assert "🧩 Purpose" in body
    assert "- Updates app logic." in body
    assert "⚙️ Changes" in body
    assert "- App returns JSON." in body
    assert "⚠️ Risks" in body
    assert "- Needs extra tests." in body
    assert "- High-risk files modified: core/app.py" in body
    assert "- Missing related tests covering modified code." in body
    assert "✅ Suggested Actions" in body
    assert "- Add integration test." in body
    assert "- Add unit tests covering the modified functions." in body
    assert "- Perform a focused review of the high-risk modules that changed." in body
