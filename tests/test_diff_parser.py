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
    change = next(
        fc for fc in file_diff.function_changes if fc.name == "new_helper")
    assert change.change_type == "added"


def test_python_parser_captures_update_pr_body_function():
    patch = """@@
-def update_pr_body(repo_full_name: str, pr_number: int, body: str, marker: str = "<marker>") -> None:
-    return False
+def update_pr_body(repo_full_name: str, pr_number: int, body: str, marker: str = "<marker>") -> None:
+    return True
"""
    pr_file = PullRequestFile(
        filename="diffscribe/github_client.py",
        status="modified",
        additions=2,
        deletions=0,
        changes=2,
        patch=patch,
    )
    parser = DiffParser()
    parsed = parser.parse_pull_request(build_pr(pr_file))
    file_diff = parsed.files[0]
    assert file_diff.language == "python"
    assert any(change.name ==
               "update_pr_body" for change in file_diff.function_changes)


def test_python_parser_detects_renamed_function():
    patch = """@@
-def old_name():
-    return False
+def new_name():
+    return True
"""
    pr_file = PullRequestFile(
        filename="core/utils.py",
        status="modified",
        additions=2,
        deletions=2,
        changes=4,
        patch=patch,
    )
    parser = DiffParser()
    parsed = parser.parse_pull_request(build_pr(pr_file))
    file_diff = parsed.files[0]
    rename_change = next(
        fc for fc in file_diff.function_changes if fc.name == "new_name"
    )
    assert rename_change.change_type == "renamed"
    assert rename_change.previous_name == "old_name"


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
    assert any(change.change_type ==
               "modified" for change in file_diff.function_changes)


def test_typescript_parser_detects_added_function():
    patch = """@@
+export function newHelper(): string {
+  return "ok";
+}
"""
    pr_file = PullRequestFile(
        filename="src/helpers.ts",
        status="modified",
        additions=3,
        deletions=0,
        changes=3,
        patch=patch,
    )
    parser = DiffParser()
    parsed = parser.parse_pull_request(build_pr(pr_file))
    file_diff = parsed.files[0]
    assert file_diff.language == "typescript"
    assert any(change.name ==
               "newHelper" for change in file_diff.function_changes)


def test_parser_ignores_comment_only_change():
    patch = """@@
-# existing comment
+# updated comment
"""
    pr_file = PullRequestFile(
        filename="src/module.py",
        status="modified",
        additions=1,
        deletions=1,
        changes=2,
        patch=patch,
    )
    parser = DiffParser()
    parsed = parser.parse_pull_request(build_pr(pr_file))
    assert parsed.files == []


def test_parser_ignores_trivial_module_change():
    patch = """@@
-value = 1
+value = 2
"""
    pr_file = PullRequestFile(
        filename="src/config.py",
        status="modified",
        additions=1,
        deletions=1,
        changes=2,
        patch=patch,
    )
    parser = DiffParser()
    parsed = parser.parse_pull_request(build_pr(pr_file))
    assert parsed.files == []


def test_parser_ignores_pyc_files():
    pr_file = PullRequestFile(
        filename="diffscribe/__pycache__/cli.cpython-313.pyc",
        status="modified",
        additions=0,
        deletions=0,
        changes=0,
        patch=None,
    )
    parser = DiffParser()
    parsed = parser.parse_pull_request(build_pr(pr_file))
    assert parsed.files == []
