#!/usr/bin/env python3
"""Evaluate enterprise tfplan2md policy rules in CI/CD pipelines."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import Any


DENIED_EXIT_CODE = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate custom tfplan2md policy rules for enterprise pipelines.")
    parser.add_argument("--policy", required=True, help="Path to a JSON policy file.")
    parser.add_argument("--plan-json", help="Optional Terraform plan JSON used to detect whether changes exist.")
    parser.add_argument("--context", help="Optional JSON file with policy context values.")
    parser.add_argument("--actor", help="Actor name, email, or UUID. Overrides environment/context values.")
    parser.add_argument("--target-branch", help="Target branch for the change. Overrides environment/context values.")
    parser.add_argument("--source-branch", help="Source branch for the change. Overrides environment/context values.")
    parser.add_argument("--has-changes", choices=["true", "false"], help="Whether Terraform changes exist. Overrides plan detection.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"Cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error

    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def detect_has_changes(plan_json_path: str | None) -> bool:
    if not plan_json_path:
        return False

    plan = load_json(plan_json_path)
    for resource_change in plan.get("resource_changes", []):
        actions = resource_change.get("change", {}).get("actions", [])
        if actions and actions != ["no-op"]:
            return True
    return False


def build_context(args: argparse.Namespace) -> dict[str, Any]:
    context = load_json(args.context) if args.context else {}
    has_changes = detect_has_changes(args.plan_json)
    if args.has_changes is not None:
        has_changes = args.has_changes == "true"

    actor = args.actor or context.get("actor") or os.getenv("TFPLAN2MD_ACTOR") or os.getenv("BITBUCKET_STEP_TRIGGERER_UUID") or os.getenv("BITBUCKET_COMMIT_AUTHOR")
    target_branch = (
        args.target_branch
        or context.get("targetBranch")
        or os.getenv("TFPLAN2MD_TARGET_BRANCH")
        or os.getenv("BITBUCKET_PR_DESTINATION_BRANCH")
        or os.getenv("BITBUCKET_BRANCH")
    )
    source_branch = args.source_branch or context.get("sourceBranch") or os.getenv("TFPLAN2MD_SOURCE_BRANCH") or os.getenv("BITBUCKET_BRANCH")

    context.update(
        {
            "actor": actor,
            "actorUuid": context.get("actorUuid") or os.getenv("BITBUCKET_STEP_TRIGGERER_UUID"),
            "actorEmail": context.get("actorEmail") or os.getenv("BITBUCKET_COMMIT_AUTHOR"),
            "targetBranch": target_branch,
            "sourceBranch": source_branch,
            "hasChanges": has_changes,
        }
    )
    return context


def normalize_to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def matches_any(value: Any, patterns: list[Any]) -> bool:
    if not patterns:
        return True
    if value is None:
        return False
    text = str(value)
    return any(fnmatch.fnmatchcase(text, str(pattern)) for pattern in patterns)


def actor_matches(context: dict[str, Any], patterns: list[Any]) -> bool:
    if not patterns:
        return True
    actor_values = [context.get("actor"), context.get("actorUuid"), context.get("actorEmail")]
    return any(matches_any(value, patterns) for value in actor_values if value)


def when_matches(conditions: dict[str, Any], context: dict[str, Any]) -> bool:
    for key, expected in conditions.items():
        actual = context.get(key)
        if isinstance(expected, list):
            if not matches_any(actual, expected):
                return False
        elif actual != expected:
            return False
    return True


def allow_matches(allow: dict[str, Any], context: dict[str, Any]) -> tuple[bool, list[str]]:
    failures = []
    if not actor_matches(context, normalize_to_list(allow.get("actors"))):
        failures.append(f"actor '{context.get('actor')}' is not allowed")
    if not matches_any(context.get("targetBranch"), normalize_to_list(allow.get("targetBranches"))):
        failures.append(f"target branch '{context.get('targetBranch')}' is not allowed")
    if not matches_any(context.get("sourceBranch"), normalize_to_list(allow.get("sourceBranches"))):
        failures.append(f"source branch '{context.get('sourceBranch')}' is not allowed")
    return not failures, failures


def evaluate_policy(policy: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    rules = policy.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("Policy field 'rules' must be an array.")

    failures = []
    matched_rules = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"Rule at index {index} must be an object.")

        name = rule.get("name", f"rule-{index + 1}")
        when = rule.get("when", {})
        if not isinstance(when, dict):
            raise ValueError(f"Rule '{name}' field 'when' must be an object.")
        if not when_matches(when, context):
            continue

        matched_rules.append(name)
        allow = rule.get("allow", {})
        if not isinstance(allow, dict):
            raise ValueError(f"Rule '{name}' field 'allow' must be an object.")
        allowed, reasons = allow_matches(allow, context)
        if not allowed:
            failures.append(
                {
                    "rule": name,
                    "message": rule.get("message", "Policy rule denied this change."),
                    "reasons": reasons,
                }
            )

    return {
        "allowed": not failures,
        "matchedRules": matched_rules,
        "failures": failures,
        "context": context,
    }


def print_result(result: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    if result["allowed"]:
        print("tfplan2md policy: allowed")
        if result["matchedRules"]:
            print("Matched rules: " + ", ".join(result["matchedRules"]))
        return

    print("tfplan2md policy: denied")
    for failure in result["failures"]:
        print(f"- {failure['rule']}: {failure['message']}")
        for reason in failure["reasons"]:
            print(f"  - {reason}")


def main() -> int:
    args = parse_args()
    try:
        policy = load_json(args.policy)
        context = build_context(args)
        result = evaluate_policy(policy, context)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print_result(result, args.format)
    return 0 if result["allowed"] else DENIED_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
