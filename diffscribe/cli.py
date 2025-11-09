from __future__ import annotations
from .living_docs import LivingDocsGenerator, commit_living_doc
from .output_manager import CommentFormatter
from .risk_analysis import RiskAnalyzer
from .models import AnalysisOutput
from .llm_summarizer import LLMSummarizer
from .diff_parser import DiffParser
from .github_client import GitHubClient

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import importlib


def _load_dotenv_factory() -> callable:
    try:
        module = importlib.import_module("dotenv")
        return getattr(module, "load_dotenv")
    except (ImportError, AttributeError):  # pragma: no cover
        def _noop() -> None:
            return None

        return _noop


load_dotenv = _load_dotenv_factory()


logger = logging.getLogger("diffscribe")


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def load_event_payload(event_path: Path) -> Dict[str, Any]:
    if not event_path.exists():
        raise FileNotFoundError(
            f"GitHub event payload not found at {event_path}")
    with event_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DiffScribe GitHub integration CLI")
    parser.add_argument("--event-path", type=Path, required=True,
                        help="Path to the GitHub event payload JSON file.")
    parser.add_argument("--output", type=Path, default=Path(
        "diffscribe_pr_snapshot.json"), help="Where to write PR snapshot JSON.")
    parser.add_argument("--base-url", type=str, default=None,
                        help="Optional GitHub Enterprise base URL.")
    parser.add_argument("--skip-comment", action="store_true",
                        help="Skip posting/updating the PR comment.")
    parser.add_argument("--enable-living-docs", action="store_true",
                        help="Generate living documentation markdown.")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs/diffs"),
                        help="Directory for living documentation output.")
    parser.add_argument("--commit-docs", action="store_true",
                        help="Commit living documentation changes after generation.")
    parser.add_argument("--update-description", action="store_true",
                        help="Update the PR description with the DiffScribe summary instead of commenting.")
    parser.add_argument("--summary-mode", choices=["concise", "detailed"], default=os.getenv(
        "DIFFSCRIBE_SUMMARY_MODE", "concise"), help="Choose summary mode: concise (default) or detailed.")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable debug logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv or sys.argv[1:])
    configure_logging(args.verbose)

    event_payload = load_event_payload(args.event_path)

    repo_full_name = event_payload.get("repository", {}).get(
        "full_name") or os.getenv("GITHUB_REPOSITORY")
    if not repo_full_name:
        logger.error(
            "Repository full name not found in event payload or environment.")
        return 1

    pr_number = event_payload.get("number") or event_payload.get(
        "pull_request", {}).get("number")
    if not pr_number:
        logger.error("Pull request number not found in event payload.")
        return 1

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN is required to access the GitHub API.")
        return 1

    client = GitHubClient(token=token, base_url=args.base_url)
    pr_number_int = int(pr_number)
    pr_info = client.fetch_pull_request(
        repo_full_name=repo_full_name, pr_number=pr_number_int)
    env_enable_docs = os.getenv("ENABLE_LIVING_DOCS", "").lower() == "true"
    env_commit_docs = os.getenv("COMMIT_LIVING_DOCS", "").lower() == "true"

    enable_living_docs = args.enable_living_docs or env_enable_docs
    commit_docs = args.commit_docs or env_commit_docs

    diff_parser = DiffParser()
    parsed_diff = diff_parser.parse_pull_request(pr_info)

    risk_analyzer = RiskAnalyzer()
    risk_assessment = risk_analyzer.assess(pr_info, parsed_diff)

    summarizer = LLMSummarizer()
    ai_summary = summarizer.summarize(
        parsed_diff, risk_assessment=risk_assessment, mode=args.summary_mode)
    analysis_output = AnalysisOutput(
        parsed_diff=parsed_diff, ai_summary=ai_summary, risk_assessment=risk_assessment)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(analysis_output.to_dict(), handle, indent=2)

    logger.info("Wrote analysis output to %s", args.output.resolve())

    doc_path = None
    if enable_living_docs:
        generator = LivingDocsGenerator(args.docs_dir)
        doc_path = generator.generate(pr_info, analysis_output)
        logger.info("Generated living documentation at %s", doc_path.resolve())
        if commit_docs:
            try:
                commit_living_doc(doc_path, pr_number_int)
                logger.info("Committed living documentation changes.")
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to commit living documentation changes: %s", exc)

    formatter = CommentFormatter()
    rendered_body = formatter.render(
        analysis_output,
        include_function_changes=args.summary_mode == "detailed",
    )

    if args.update_description:
        client.update_pr_body(
            repo_full_name=repo_full_name, pr_number=pr_number_int, body=rendered_body)

    if not args.skip_comment and not args.update_description:
        client.upsert_pr_comment(
            repo_full_name=repo_full_name, pr_number=pr_number_int, body=rendered_body)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
