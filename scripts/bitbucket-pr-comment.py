#!/usr/bin/env python3
"""Create or update a Bitbucket pull request comment for a tfplan2md report."""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_MARKER = "<!-- tfplan2md-bitbucket-report -->"
DEFAULT_MAX_COMMENT_CHARS = 60000
BITBUCKET_API_ROOT = "https://api.bitbucket.org/2.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post a tfplan2md report to a Bitbucket PR, falling back to an HTML artifact link when the report is too large."
    )
    parser.add_argument("--report", required=True, help="Path to the generated tfplan2md markdown report.")
    parser.add_argument("--artifact-url", default=os.getenv("TFPLAN2MD_ARTIFACT_URL"), help="URL to the full report artifact.")
    parser.add_argument("--title", default="Terraform plan report", help="Heading used in the PR comment.")
    parser.add_argument("--marker", default=DEFAULT_MARKER, help="Hidden marker used to update an existing bot comment.")
    parser.add_argument(
        "--max-comment-chars",
        type=int,
        default=int(os.getenv("TFPLAN2MD_MAX_COMMENT_CHARS", str(DEFAULT_MAX_COMMENT_CHARS))),
        help=f"Maximum inline comment size before artifact fallback is used (default: {DEFAULT_MAX_COMMENT_CHARS}).",
    )
    parser.add_argument("--workspace", default=os.getenv("BITBUCKET_WORKSPACE"), help="Bitbucket workspace slug.")
    parser.add_argument("--repo-slug", default=os.getenv("BITBUCKET_REPO_SLUG"), help="Bitbucket repository slug.")
    parser.add_argument("--pull-request-id", default=os.getenv("BITBUCKET_PR_ID"), help="Bitbucket pull request ID.")
    parser.add_argument(
        "--oidc-token",
        default=os.getenv("BITBUCKET_STEP_OIDC_TOKEN"),
        help="Bitbucket Pipelines OIDC token. Enable 'oidc: true' on the pipeline step.",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("BITBUCKET_API_BASE_URL", BITBUCKET_API_ROOT),
        help="Bitbucket-compatible API root. Enterprise OIDC gateways can override this URL.",
    )
    parser.add_argument("--username", default=os.getenv("BITBUCKET_USERNAME"), help=argparse.SUPPRESS)
    parser.add_argument(
        "--app-password",
        default=os.getenv("BITBUCKET_APP_PASSWORD"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--token", default=os.getenv("BITBUCKET_TOKEN"), help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help="Print the comment body without calling the Bitbucket API.")
    parser.add_argument("--comment-file", help="Write the generated comment body to a file for diagnostics or artifacts.")
    return parser.parse_args()


def build_comment_body(report: str, title: str, marker: str, max_comment_chars: int, artifact_url: str | None) -> str:
    inline_body = f"{marker}\n\n### {title}\n\n{report.strip()}\n"
    if len(inline_body) <= max_comment_chars:
        return inline_body

    if not artifact_url:
        raise ValueError("--artifact-url or TFPLAN2MD_ARTIFACT_URL is required when the report exceeds the comment-size limit.")

    escaped_url = html.escape(artifact_url, quote=True)
    return "\n".join(
        [
            marker,
            "",
            f"### {title}",
            "",
            f"The full tfplan2md report is {len(inline_body):,} characters, which exceeds the configured Bitbucket comment limit of {max_comment_chars:,} characters.",
            "",
            f'View the full report artifact: <a href="{escaped_url}">tfplan2md report artifact</a>',
            "",
            f"Artifact URL: {artifact_url}",
            "",
        ]
    )


def get_auth_header(oidc_token: str | None, username: str | None, app_password: str | None, token: str | None) -> str:
    if oidc_token:
        return f"Bearer {oidc_token}"
    if token:
        return f"Bearer {token}"
    if username and app_password:
        credentials = base64.b64encode(f"{username}:{app_password}".encode("utf-8")).decode("ascii")
        return f"Basic {credentials}"
    raise ValueError("Enable Bitbucket Pipelines OIDC and pass BITBUCKET_STEP_OIDC_TOKEN to post PR comments.")


def api_request(url: str, method: str, auth_header: str, payload: dict | None = None) -> dict:
    data = None
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Bitbucket API request failed ({error.code}): {error_body}") from error


def comments_url(api_base_url: str, workspace: str, repo_slug: str, pull_request_id: str) -> str:
    encoded_workspace = urllib.parse.quote(workspace, safe="")
    encoded_repo_slug = urllib.parse.quote(repo_slug, safe="")
    encoded_pr_id = urllib.parse.quote(pull_request_id, safe="")
    return f"{api_base_url.rstrip('/')}/repositories/{encoded_workspace}/{encoded_repo_slug}/pullrequests/{encoded_pr_id}/comments"


def find_existing_comment(url: str, marker: str, auth_header: str) -> int | None:
    next_url = f"{url}?pagelen=100"
    while next_url:
        response = api_request(next_url, "GET", auth_header)
        for comment in response.get("values", []):
            raw = comment.get("content", {}).get("raw", "")
            if marker in raw:
                return comment.get("id")
        next_url = response.get("next")
    return None


def upsert_comment(url: str, marker: str, comment_body: str, auth_header: str) -> None:
    payload = {"content": {"raw": comment_body}}
    existing_comment_id = find_existing_comment(url, marker, auth_header)
    if existing_comment_id is None:
        api_request(url, "POST", auth_header, payload)
        print("Created Bitbucket PR comment.")
        return

    api_request(f"{url}/{existing_comment_id}", "PUT", auth_header, payload)
    print(f"Updated Bitbucket PR comment {existing_comment_id}.")


def validate_comment_target(args: argparse.Namespace) -> tuple[str, str, str]:
    missing = [
        name
        for name, value in [
            ("BITBUCKET_WORKSPACE", args.workspace),
            ("BITBUCKET_REPO_SLUG", args.repo_slug),
            ("BITBUCKET_PR_ID", args.pull_request_id),
        ]
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required Bitbucket PR context: {', '.join(missing)}.")
    return args.workspace, args.repo_slug, args.pull_request_id


def main() -> int:
    args = parse_args()
    report_path = Path(args.report)
    if not report_path.is_file():
        print(f"Error: report file not found: {report_path}", file=sys.stderr)
        return 2

    try:
        report = report_path.read_text(encoding="utf-8")
        comment_body = build_comment_body(report, args.title, args.marker, args.max_comment_chars, args.artifact_url)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if args.comment_file:
        Path(args.comment_file).write_text(comment_body, encoding="utf-8")

    if args.dry_run:
        print(comment_body)
        return 0

    try:
        workspace, repo_slug, pull_request_id = validate_comment_target(args)
        auth_header = get_auth_header(args.oidc_token, args.username, args.app_password, args.token)
        upsert_comment(comments_url(args.api_base_url, workspace, repo_slug, pull_request_id), args.marker, comment_body, auth_header)
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
