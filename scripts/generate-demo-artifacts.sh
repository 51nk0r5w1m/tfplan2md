#!/usr/bin/env bash
# Generate Demo Artifacts Script
#
# Purpose: Regenerate all demo markdown artifacts from the current codebase.
# This ensures UAT tests validate the actual behavior of the tool, not stale output.
#
# Usage: scripts/generate-demo-artifacts.sh

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Navigate to repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

GO_MODULE_DIR="$REPO_ROOT/src-go"
TFPLAN2MD_BIN="$GO_MODULE_DIR/tfplan2md"

if [[ ! -d "$GO_MODULE_DIR" || ! -f "$GO_MODULE_DIR/go.mod" ]]; then
  log_error "Go module not found at $GO_MODULE_DIR"
  log_error "The Go implementation must be in place before generating artifacts."
  exit 1
fi

log_info "Building tfplan2md (Go, Release)..."
(cd "$GO_MODULE_DIR" && CGO_ENABLED=0 go build -o tfplan2md ./cmd/tfplan2md)

run_tfplan2md() {
  "$TFPLAN2MD_BIN" "$@"
}

generate_artifact() {
  local label="$1"
  local output="$2"
  shift 2

  log_info "Generating $output ($label)..."
  run_tfplan2md --output "$output" "$@"

  if [[ ! -s "$output" ]]; then
    log_error "Generated artifact is empty or missing: $output"
    exit 1
  fi

  if ! head -1 "$output" | grep -q '^#'; then
    log_error "Generated artifact does not appear to be valid markdown: $output"
    exit 1
  fi

  log_info "✓ $output generated successfully"
}

# ============================================================================
# Part 1: Generate /artifacts/*.md (used for UAT)
# ============================================================================

generate_artifact "inline-diff, Azure DevOps UAT" \
  artifacts/comprehensive-demo.md \
  --principal-mapping examples/comprehensive-demo/demo-principals.json \
  --code-analysis-results "examples/static-analysis/*.sarif" \
  examples/comprehensive-demo/plan.json

generate_artifact "GitHub UAT" \
  artifacts/comprehensive-demo-simple-diff.md \
  --principal-mapping examples/comprehensive-demo/demo-principals.json \
  --code-analysis-results "examples/static-analysis/*.sarif" \
  --render-target github \
  examples/comprehensive-demo/plan.json

generate_artifact "role assignments with principal mapping" \
  artifacts/role.md \
  --principal-mapping examples/comprehensive-demo/demo-principals.json \
  src-go/testdata/role-assignments.json

generate_artifact "role assignments with demo principal mapping" \
  artifacts/role-default.md \
  --principal-mapping examples/role-assignments-principals.json \
  src-go/testdata/role-assignments.json

generate_artifact "APIM display enhancements demo" \
  artifacts/apim-display-enhancements-demo.md \
  examples/apim-display-enhancements.json

generate_artifact "refactoring demo, inline-diff" \
  artifacts/refactoring-demo.md \
  examples/refactoring-demo.json

generate_artifact "refactoring demo, GitHub render target" \
  artifacts/refactoring-demo-simple-diff.md \
  --render-target github \
  examples/refactoring-demo.json

generate_artifact "comprehensive demo with code analysis" \
  artifacts/static-analysis-comprehensive-demo.md \
  --code-analysis-results "examples/static-analysis/*.sarif" \
  examples/comprehensive-demo/plan.json

# Note: uat-minimal.md is a static handcrafted file, not generated

generate_artifact "AzAPI create demo" \
  artifacts/azapi-create-demo.md \
  examples/azapi-create.json

generate_artifact "AzAPI update demo" \
  artifacts/azapi-update-demo.md \
  examples/azapi-update.json

generate_artifact "AzAPI complex demo" \
  artifacts/azapi-complex-demo.md \
  examples/azapi-complex.json

generate_artifact "AzureAD enhancements demo" \
  artifacts/azuread-enhancements-demo.md \
  --principal-mapping examples/principal-mapping-azuread.json \
  examples/azuread-resources-demo.json

generate_artifact "Azure display enhancements demo" \
  artifacts/azure-display-enhancements-demo.md \
  examples/azure-display-enhancements.json

generate_artifact "Azure display enhancements, GitHub render target" \
  artifacts/azure-display-enhancements-demo-simple-diff.md \
  --render-target github \
  examples/azure-display-enhancements.json

# ============================================================================
# Part 2: Generate examples/comprehensive-demo/*.md (documentation samples)
# ============================================================================

generate_artifact "default template" \
  examples/comprehensive-demo/report.md \
  --principal-mapping examples/comprehensive-demo/demo-principals.json \
  --code-analysis-results "examples/static-analysis/*.sarif" \
  examples/comprehensive-demo/plan.json

generate_artifact "with --show-sensitive" \
  examples/comprehensive-demo/report-with-sensitive.md \
  --principal-mapping examples/comprehensive-demo/demo-principals.json \
  --code-analysis-results "examples/static-analysis/*.sarif" \
  --show-sensitive \
  examples/comprehensive-demo/plan.json

generate_artifact "summary template" \
  examples/comprehensive-demo/report-summary.md \
  --template summary \
  examples/comprehensive-demo/plan.json

# ============================================================================
# Part 3: Generate additional artifacts (examples)
# ============================================================================

generate_artifact "AzAPI nested grouping demo" \
  artifacts/azapi-nested-grouping-demo.md \
  src-go/testdata/azapi-complex-nested-plan.json

generate_artifact "AzAPI UAT combined demo" \
  artifacts/azapi-uat-combined.md \
  src-go/testdata/azapi-complex-nested-plan.json

generate_artifact "comprehensive demo with nested principals" \
  artifacts/comprehensive-demo-nested.md \
  --principal-mapping examples/comprehensive-demo/demo-principals-nested.json \
  --code-analysis-results "examples/static-analysis/*.sarif" \
  examples/comprehensive-demo/plan.json

generate_artifact "code analysis example" \
  examples/code-analysis/report.md \
  --code-analysis-results "examples/code-analysis/analysis.sarif" \
  examples/code-analysis/plan.json

generate_artifact "firewall with static analysis example" \
  examples/firewall-with-static-analysis/report.md \
  --code-analysis-results "examples/firewall-with-static-analysis/analysis.sarif" \
  examples/firewall-with-static-analysis/plan.json

# ============================================================================
# Part 4: Generate additional UAT artifacts
# ============================================================================

generate_artifact "Azure RM batch 2 feature test" \
  artifacts/azure-rm-batch-2-feature-test.md \
  src-go/testdata/azure-rm-batch-2-feature-test-plan.json

generate_artifact "Azure RM batch 2 feature test, GitHub render target" \
  artifacts/azure-rm-batch-2-feature-test-simple-diff.md \
  --render-target github \
  src-go/testdata/azure-rm-batch-2-feature-test-plan.json

generate_artifact "parent-child grouping UAT" \
  artifacts/parent-child-resource-grouping-uat.md \
  src-go/testdata/parent-child-resource-grouping-uat-plan.json

generate_artifact "Azure RM parent-child demo" \
  artifacts/azure-rm-parent-child-demo.md \
  src-go/testdata/multiple-parents-same-type.json

generate_artifact "VNet separate subnets test" \
  artifacts/test-vnet-separate.md \
  src-go/testdata/azurerm-vnet-separate-subnets-plan.json

generate_artifact "firewall application rules UAT" \
  artifacts/firewall-application-rules-uat.md \
  examples/firewall-application-rules-demo/plan.json

generate_artifact "firewall rules example" \
  examples/firewall-rules-demo/firewall-rules.md \
  --principal-mapping examples/firewall-rules-demo/principals.json \
  examples/firewall-rules-demo/plan.json

generate_artifact "API management policy example" \
  examples/api-management-policy-demo/output.md \
  examples/api-management-policy-demo/plan.json

generate_artifact "Azure DevOps repo mapping and icons (feature 096 UAT)" \
  artifacts/azuredevops-feature-096.md \
  --principal-mapping examples/comprehensive-demo/demo-principals.json \
  examples/azuredevops/terraform_plan.json

log_info "All demo artifacts generated successfully"
