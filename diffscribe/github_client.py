from __future__ import annotations

import logging
from typing import Optional

from github import Github, Repository, PullRequest

from .models import PullRequestInfo, PullRequestFile

DEFAULT_COMMENT_MARKER = "<!-- DiffScribe -->"

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self, token: str, base_url: Optional[str] = None) -> None:
        if base_url:
            self._github = Github(login_or_token=token, base_url=base_url)
        else:
            self._github = Github(login_or_token=token)

    def _get_repo(self, full_name: str) -> Repository.Repository:
        logger.debug("Fetching repository %s", full_name)
        return self._github.get_repo(full_name)

    def fetch_pull_request(self, repo_full_name: str, pr_number: int) -> PullRequestInfo:
        repo = self._get_repo(repo_full_name)
        logger.debug("Fetching PR #%s from %s", pr_number, repo_full_name)
        pull_request = repo.get_pull(pr_number)
        files = [
            PullRequestFile(
                filename=file.filename,
                status=file.status,
                additions=file.additions,
                deletions=file.deletions,
                changes=file.changes,
                patch=file.patch,
                sha=file.sha,
            )
            for file in pull_request.get_files()
        ]

        labels = [label.name for label in pull_request.get_labels()]
        pr_info = PullRequestInfo(
            number=pull_request.number,
            title=pull_request.title,
            body=pull_request.body,
            author=pull_request.user.login if pull_request.user else "unknown",
            url=pull_request.html_url,
            base_branch=pull_request.base.ref,
            head_branch=pull_request.head.ref,
            created_at=pull_request.created_at.isoformat() if pull_request.created_at else "",
            updated_at=pull_request.updated_at.isoformat() if pull_request.updated_at else "",
            files=files,
            labels=labels,
            draft=pull_request.draft,
            is_mergeable=pull_request.mergeable,
        )
        logger.debug("Fetched PR info: %s", pr_info)
        return pr_info

    def upsert_pr_comment(self, repo_full_name: str, pr_number: int, body: str, marker: str = DEFAULT_COMMENT_MARKER) -> None:
        repo = self._get_repo(repo_full_name)
        issue = repo.get_issue(number=pr_number)
        full_body = body if marker in body else f"{marker}\n\n{body}"

        for comment in issue.get_comments():
            if comment.body and marker in comment.body:
                if comment.body.strip() == full_body.strip():
                    logger.info(
                        "Existing DiffScribe comment is up to date; no changes posted.")
                    return
                comment.edit(full_body)
                logger.info(
                    "Updated existing DiffScribe comment on PR #%s.", pr_number)
                return

        issue.create_comment(full_body)
        logger.info("Posted new DiffScribe comment on PR #%s.", pr_number)
