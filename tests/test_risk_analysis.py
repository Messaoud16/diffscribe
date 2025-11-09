from diffscribe.models import PullRequestFile, PullRequestInfo, ParsedDiff
from diffscribe.risk_analysis import RiskAnalyzer


def build_pr(files: list[PullRequestFile]) -> PullRequestInfo:
    return PullRequestInfo(
        number=1,
        title="Risk test",
        body="",
        author="tester",
        url="http://example.com",
        base_branch="main",
        head_branch="feature",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        files=files,
        labels=[],
        draft=False,
        is_mergeable=True,
    )


def build_parsed(pr_info: PullRequestInfo) -> ParsedDiff:
    return ParsedDiff(pull_request=pr_info, files=[])


def test_risk_analyzer_flags_high_risk_and_missing_tests():
    files = [
        PullRequestFile(
            filename="core/service.py",
            status="modified",
            additions=10,
            deletions=2,
            changes=12,
            patch="+print('hello')",
        ),
        PullRequestFile(
            filename="README.md",
            status="modified",
            additions=1,
            deletions=0,
            changes=1,
            patch="+Docs",
        ),
    ]
    pr_info = build_pr(files)
    analyzer = RiskAnalyzer()
    assessment = analyzer.assess(pr_info, build_parsed(pr_info))

    assert "core/service.py" in assessment.high_risk_files
    assert assessment.missing_tests


def test_risk_analyzer_detects_deprecated_api():
    files = [
        PullRequestFile(
            filename="src/component.jsx",
            status="modified",
            additions=2,
            deletions=0,
            changes=2,
            patch="+componentWillMount()",
        ),
    ]
    pr_info = build_pr(files)
    analyzer = RiskAnalyzer()
    assessment = analyzer.assess(pr_info, build_parsed(pr_info))

    assert any("componentWillMount" in item for item in assessment.deprecated_apis)

