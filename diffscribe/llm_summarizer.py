from __future__ import annotations

import json
import logging
import os
from typing import Optional

from openai import OpenAI, OpenAIError

from .models import AISummary, ParsedDiff, RiskAssessment

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"


class LLMSummarizer:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL, temperature: float = 0.2) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.temperature = temperature
        self._client: Optional[OpenAI] = None
        if self.api_key:
            self._client = OpenAI(api_key=self.api_key)
        else:
            logger.warning(
                "OPENAI_API_KEY not provided; summarizer will return fallback content.")

    def summarize(self, parsed_diff: ParsedDiff, risk_assessment: RiskAssessment | None = None) -> AISummary:
        if not self._client:
            return AISummary(
                summary="AI summarization unavailable because OPENAI_API_KEY is not configured.",
                behavior_changes=[],
                risks=[],
                suggested_actions=[],
                model=None,
                raw_response=None,
            )

        prompt_payload = self._build_prompt_payload(
            parsed_diff, risk_assessment)
        system_prompt = (
            "You are DiffScribe, an assistant that creates concise, reviewer-focused pull request summaries. "
            "Given structured PR data, respond with a JSON object containing keys: "
            "`summary` (one short paragraph describing the PR intent), "
            "`behavior_changes` (array of bullet-ready strings, one per meaningful function/class change in the format "
            "`FunctionName()` or `ClassName.method()` followed by an em dash and a short plain-English description of what changed/why), "
            "`risks` (array highlighting concrete concerns such as unused variables, potential infinite loops, shared module impacts, or security-sensitive changes), "
            "and `suggested_actions` (array of specific follow-up steps like adding tests or removing dead code). "
            "Ignore formatting-only edits, module-level tweaks without behavioral impact, and helper functions that introduce no new risk. "
            "Keep every item plain-English, actionable, and tied to the function/module name. "
            "Do not add extra keys."
        )
        user_prompt = json.dumps(prompt_payload, indent=2)

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"PR DATA:\n{user_prompt}"},
                ],
            )
        except OpenAIError as exc:
            logger.error("OpenAI summarization failed: %s", exc)
            return AISummary(
                summary="AI summarization failed due to API error; see logs for details.",
                behavior_changes=[],
                risks=[str(exc)],
                suggested_actions=[],
                model=self.model,
                raw_response=None,
            )

        message = response.choices[0].message.content if response.choices else None
        if not message:
            logger.error("OpenAI returned no content.")
            return AISummary(
                summary="AI summarization returned empty response.",
                behavior_changes=[],
                risks=[],
                suggested_actions=[],
                model=self.model,
                raw_response=None,
            )

        try:
            parsed = json.loads(message)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse JSON response; returning raw content.")
            return AISummary(
                summary=message.strip(),
                behavior_changes=[],
                risks=[],
                suggested_actions=[],
                model=self.model,
                raw_response=message,
            )

        return AISummary(
            summary=parsed.get("summary", "").strip(),
            behavior_changes=[item.strip() for item in parsed.get(
                "behavior_changes", []) if isinstance(item, str)],
            risks=[item.strip() for item in parsed.get(
                "risks", []) if isinstance(item, str)],
            suggested_actions=[item.strip() for item in parsed.get(
                "suggested_actions", []) if isinstance(item, str)],
            model=self.model,
            raw_response=message,
        )

    def _build_prompt_payload(self, parsed_diff: ParsedDiff, risk_assessment: RiskAssessment | None) -> dict:
        pr_info = parsed_diff.pull_request.to_dict()
        pr_summary = {
            "number": pr_info["number"],
            "title": pr_info["title"],
            "author": pr_info["author"],
            "body": pr_info["body"],
            "base_branch": pr_info["base_branch"],
            "head_branch": pr_info["head_branch"],
            "draft": pr_info["draft"],
            "labels": pr_info["labels"],
            "url": pr_info["url"],
        }

        files_summary = []
        for file in parsed_diff.files:
            file_entry = {
                "filename": file.filename,
                "language": file.language,
                "status": file.status,
                "previous_filename": file.previous_filename,
                "summary": file.summary,
                "additions": file.additions,
                "deletions": file.deletions,
                "function_changes": [
                    {
                        "name": change.name,
                        "change_type": change.change_type,
                        "previous_name": change.previous_name,
                        "summary": change.summary,
                        "lines_added": change.lines_added,
                        "lines_removed": change.lines_removed,
                    }
                    for change in file.function_changes
                ],
            }
            files_summary.append(file_entry)

        payload = {
            "pull_request": pr_summary,
            "files": files_summary,
        }
        if risk_assessment:
            payload["precomputed_risks"] = risk_assessment.to_dict()
        return payload
