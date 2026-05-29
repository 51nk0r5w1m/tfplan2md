#!/usr/bin/env bash
set -euo pipefail

# Prints coverage summary from a Go coverage profile.
# Usage: scripts/coverage-summary.sh [path-to-coverage.out]

coverage_path="${1:-}"

if [[ -z "$coverage_path" ]]; then
  if [[ -f "src-go/coverage.out" ]]; then
    coverage_path="src-go/coverage.out"
  else
    matches=(src-go/coverage*.out)
    if (( ${#matches[@]} > 0 )); then
      coverage_path="${matches[0]}"
    fi
  fi
fi

if [[ -z "$coverage_path" || ! -f "$coverage_path" ]]; then
  echo "Coverage file not found. Pass the coverage.out path explicitly." >&2
  echo "Generate with: cd src-go && go test -coverprofile=coverage.out ./..." >&2
  exit 1
fi

go tool cover -func="$coverage_path" | grep "^total:"
