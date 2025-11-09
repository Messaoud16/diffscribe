from diffscribe.diff_parser import DiffParser
from diffscribe.models import PullRequestFile, PullRequestInfo


def build_pr(pr_file: PullRequestFile) -> PullRequestInfo:
    return PullRequestInfo(
        number=1,
        title="Test PR",
        body="Adds helper",
        author="tester",
        url="http://example.com",
        base_branch="main",
        head_branch="feature",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        files=[pr_file],
        labels=[],
        draft=False,
        is_mergeable=True,
    )


def test_python_parser_detects_added_function():
    patch = """@@
+def new_helper():
+    return True
"""
    pr_file = PullRequestFile(
        filename="core/utils.py",
        status="modified",
        additions=2,
        deletions=0,
        changes=2,
        patch=patch,
    )
    parser = DiffParser()
    parsed = parser.parse_pull_request(build_pr(pr_file))
    assert len(parsed.files) == 1
    file_diff = parsed.files[0]
    assert file_diff.language == "python"
    change = next(fc for fc in file_diff.function_changes if fc.name == "new_helper")
    assert change.change_type == "added"


def test_js_parser_detects_modified_function():
    patch = """@@ function doThing()
-function doThing() {
-  return false;
-}
+function doThing() {
+  return true;
+}
"""
    pr_file = PullRequestFile(
        filename="src/doThing.js",
        status="modified",
        additions=3,
        deletions=3,
        changes=6,
        patch=patch,
    )
    parser = DiffParser()
    parsed = parser.parse_pull_request(build_pr(pr_file))
    assert len(parsed.files) == 1
    file_diff = parsed.files[0]
    assert file_diff.language == "javascript"
    assert any(change.change_type == "modified" for change in file_diff.function_changes)

