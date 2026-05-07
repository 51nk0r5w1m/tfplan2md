#!/usr/bin/env bash
set -euo pipefail

# Lists packages with the lowest function coverage from a Go coverage profile.
# Usage: scripts/coverage-low-branches.sh [count] [path-to-coverage.out]

count="${1:-30}"
coverage_path="${2:-}"

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

# Use go tool cover to display per-function coverage and sort by lowest
go tool cover -func="$coverage_path" \
  | grep -v "^total:" \
  | sort -t$'\t' -k3 -n \
  | head -n "$count"
