#!/usr/bin/env bash
# Update Test Snapshots Script
#
# Purpose: Regenerate all test snapshot files when intentional markdown changes are made.
# This script deletes existing snapshots and re-runs Go tests with UPDATE_SNAPSHOTS=1
# to capture the new expected output.
#
# Usage: scripts/update-test-snapshots.sh

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

REPO_ROOT="$(git rev-parse --show-toplevel)"
GO_MODULE_DIR="$REPO_ROOT/src-go"
SNAPSHOTS_DIR="$GO_MODULE_DIR/testdata/snapshots"

if [[ ! -d "$GO_MODULE_DIR" ]]; then
  log_error "Go module directory not found: $GO_MODULE_DIR"
  log_error "The Go implementation must exist at src-go/ before snapshots can be updated."
  exit 1
fi

if [[ ! -f "$GO_MODULE_DIR/go.mod" ]]; then
  log_error "go.mod not found in $GO_MODULE_DIR"
  exit 1
fi

# Create snapshots directory if it doesn't exist yet
mkdir -p "$SNAPSHOTS_DIR"

log_info "Deleting existing snapshot files..."
find "$SNAPSHOTS_DIR" -maxdepth 2 -type f -name '*.md' -delete 2>/dev/null || true
log_info "✓ Cleared existing snapshots"

log_info "Running snapshot tests with UPDATE_SNAPSHOTS=1 to regenerate files..."
log_info "(Tests will update snapshots instead of asserting equality)"

(
  cd "$GO_MODULE_DIR"
  UPDATE_SNAPSHOTS=1 go test -run "Snapshot" ./... -v 2>&1 || true
)

# Count generated snapshots
SNAPSHOT_COUNT=$(find "$SNAPSHOTS_DIR" -maxdepth 2 -type f -name '*.md' 2>/dev/null | wc -l)

if [[ $SNAPSHOT_COUNT -eq 0 ]]; then
  log_warn "No snapshot files were generated."
  log_warn "Either no snapshot tests exist yet, or they use a different testdata directory."
  log_warn "Check that snapshot tests write to: $SNAPSHOTS_DIR"
  exit 0
fi

log_info "✓ Generated $SNAPSHOT_COUNT new snapshot files"

log_info "Running snapshot tests again to verify..."
if (
  cd "$GO_MODULE_DIR"
  go test -run "Snapshot" ./... -v
); then
  log_info "✅ All snapshot tests pass!"
  log_info ""
  log_info "Snapshots updated successfully. Review changes with:"
  log_info "  git diff $SNAPSHOTS_DIR"
else
  log_error "Snapshot tests still failing after regeneration."
  log_error "This may indicate a non-deterministic issue in the code."
  exit 1
fi
