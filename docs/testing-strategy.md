# Testing Strategy

## Overview

The tfplan2md project uses a comprehensive testing strategy with **Go's standard `testing` package** and **testify** as the test framework. All tests are located under `src-go/` alongside the packages they test, following Go conventions.

## Test Infrastructure

- **Test Framework**: Go stdlib `testing` + `github.com/stretchr/testify` (assert/require)
- **Test Location**: `_test.go` files co-located with each `internal/` package; integration tests in `src-go/test/`
- **Test Execution**: `go test ./...` from `src-go/`, or use `scripts/test-with-timeout.sh`

### Go Test CLI Syntax

#### Running Tests
```bash
# Run all tests (from src-go/)
go test ./...

# Run with race detector (required in CI)
go test -race ./...

# Run with coverage
go test -race -coverprofile=coverage.out ./...

# Run a specific package
go test ./internal/parsing/...

# Run a specific test by exact name
go test ./internal/parsing/... -run TestParsePlan_ValidJSON

# Run table-driven subtests (use /subtest-name syntax)
go test ./internal/markdown/... -run TestRender/create_resource

# Run with verbose output
go test -v ./...

# Run fuzz tests
go test ./internal/parsing/... -fuzz=FuzzParsePlan -fuzztime=30s

# Use the timeout wrapper (recommended for CI)
scripts/test-with-timeout.sh -- go test -race ./...
```

#### Coverage
```bash
# Generate and view coverage report
go test -race -coverprofile=coverage.out ./...
go tool cover -html=coverage.out  # open in browser
go tool cover -func=coverage.out  # summary in terminal

# Coverage threshold enforcement (CI target: ≥ 80%)
go tool cover -func=coverage.out | grep "total:" | awk '{print $3}'
```

#### Build Tags
```bash
# Run integration tests (tagged separately to exclude from unit test runs)
go test -tags=integration ./...

# Run only unit tests (default, no extra flags needed)
go test ./...
```

### Why Go's stdlib testing?

**Performance**:
- Native, zero-dependency test runner built into the Go toolchain
- Parallel tests with `t.Parallel()` for fast execution
- Consistent execution time

**Diagnostics**:
- `go test -v` shows real-time test names and results
- `-race` flag detects data races at runtime
- `-timeout` flag prevents hanging tests (default 10 minutes)
- `t.Log` / `t.Logf` produce output only on failure

**Architecture**:
- **Table-driven tests**: Idiomatic Go pattern using `t.Run` subtests for broad input coverage
- **Same-package tests**: White-box tests in `package X` access unexported identifiers
- **External tests**: Black-box tests in `package X_test` test the public API
- **Built-in fuzz testing**: `go test -fuzz` for property-based edge-case coverage

### Test Configuration

Go tests use `TestMain` when per-package setup/teardown is required:

```go
// TestMain sets up shared test fixtures for the package.
func TestMain(m *testing.M) {
    // setup
    code := m.Run()
    // teardown
    os.Exit(code)
}
```

Parallelism is controlled per-test:
```go
func TestParsePlan(t *testing.T) {
    t.Parallel() // opt-in per test
    // ...
}
```

## Test Types

### Architecture Tests

Architecture rules are enforced via `golangci-lint` import analysis and Go's built-in `internal/` package visibility enforcement rather than runtime reflection tests.

**Purpose:** Prevent unintended coupling between packages, document architectural rules, and catch dependency violations during PR validation.

**Technology:** `golangci-lint` with `depguard`/`gomodguard`, plus Go toolchain's built-in `internal/` package protection.

**Documentation:** See [docs/architecture-rules.md](architecture-rules.md) for complete layer definitions.

#### Key Package Dependency Rules

- `internal/parsing` must NOT import `internal/markdown` (prevents circular dependencies)
- `internal/markdown` must NOT import `internal/providers` (general rendering independent of providers)
- `cmd/` packages import `internal/` but `internal/` packages never import `cmd/`

#### Running Architecture Checks

```bash
# Run linter (includes import dependency analysis)
golangci-lint run ./...

# Check for import cycles
go build ./...  # fails on import cycles

# Verify internal/ package protection
# Any attempt to import internal/ from outside the module fails at compile time
```

#### When They Run

- **Locally:** `golangci-lint run ./...` and `go build ./...`
- **CI:** Run automatically on every PR as part of the lint job in `pr-validation.yml`

#### How Developers Interact with Architecture Checks

**If a linter reports a dependency violation:**

1. **Read the error message** — `golangci-lint` output identifies the offending import and rule
2. **Review [docs/architecture-rules.md](architecture-rules.md)** — Understand the package structure
3. **Fix the violation** — Refactor by introducing a shared interface, moving code to the appropriate package, or using dependency injection
4. **Re-run checks** — `golangci-lint run ./...`

#### References

- **Layer Definitions:** [docs/architecture-rules.md](architecture-rules.md)
- **ADR:** [ADR-007: Architecture Boundary Enforcement](adr-007-architecture-boundary-enforcement.md)

### Unit Tests

Test individual Go packages in isolation to verify correct behavior of parsing, model building, markdown rendering, and CLI argument parsing. Use table-driven tests with `t.Run` subtests:

```go
func TestParsePlan_Actions(t *testing.T) {
    t.Parallel()
    tests := []struct {
        name    string
        fixture string
        want    []string
    }{
        {"create only", "create-only-plan.json", []string{"create"}},
        {"delete only", "delete-only-plan.json", []string{"delete"}},
    }
    for _, tc := range tests {
        tc := tc
        t.Run(tc.name, func(t *testing.T) {
            t.Parallel()
            plan, err := ParsePlanFile(filepath.Join("testdata", tc.fixture))
            require.NoError(t, err)
            // assertions...
        })
    }
}
```

### Integration Tests

Test JSON parsing and markdown generation end-to-end. As the application is distributed via Docker, Docker-based integration tests verify the final CLI behavior in a containerized environment. Tag integration tests with `//go:build integration` to separate them from unit tests:

```go
//go:build integration

package integration_test
```

Run integration tests with:
```bash
go test -tags=integration -race ./test/...
```

### User Acceptance Testing (UAT)

For user-facing changes (especially markdown rendering), run UAT in real environments using **temporary pull requests** in:

- GitHub PRs in `oocx/tfplan2md-uat`
- Azure DevOps PRs in `https://dev.azure.com/oocx` (project `test`, repository `test`)

#### UAT Artifacts Strategy

UAT uses **two artifacts** for comprehensive testing:

1. **Feature-Specific Test Report** (`artifacts/<feature-slug>-uat.md`)
   - Focused on testing the specific changes in the current feature
   - Generated from a minimal test plan that exercises the feature
   - Posted as first PR comment labeled "🎯 Feature Test"
   - Defined in UAT test plan by Quality Engineer
   - Generated by Developer during implementation

2. **Comprehensive Demo** (regression test)
   - GitHub: `artifacts/comprehensive-demo-simple-diff.md`
   - Azure DevOps: `artifacts/comprehensive-demo.md`
   - Ensures no unintended side effects in other areas
   - Posted as second PR comment labeled "🔄 Regression Test"
   - Generated automatically using `generate-demo-artifacts` skill

This dual-artifact approach ensures:
- **Feature validation**: Specific changes are easy to find and test
- **Regression detection**: Unintended changes are caught
- **Testing efficiency**: Maintainer knows exactly what to focus on

#### Key Principles

1. **Markdown as PR Comment**: Generated markdown reports are posted as **PR comments** (not PR description) so actual rendering can be validated in the real PR UI.
2. **Dual Reports**: Each UAT PR contains two comments - feature-specific test and comprehensive regression test.
3. **Incremental Updates**: Updates can be posted as **new comments** so Maintainer can see progression.
4. **Autonomous Polling**: Agent polls automatically every 30 seconds without requiring Maintainer prompts.
5. **Automatic Cleanup**: UAT PRs are closed/abandoned and branches deleted after approval or abort.

#### Approval Criteria

| Platform | Approval Detected When |
|----------|----------------------|
| **GitHub** | Maintainer comments "approved", "passed", "lgtm", "accept" **OR** closes the PR |
| **Azure DevOps** | Maintainer comments "approved"/"passed"/etc. **OR** marks the latest comment thread as "Resolved" |

#### Helper Scripts

Use the scripts in `scripts/` for simplified UAT workflow:

**End-to-end UAT** (`scripts/uat-run.sh`):
```bash
# Complete UAT workflow with both artifacts (recommended)
scripts/uat-run.sh artifacts/<feature-slug>-uat.md "<validation-description>" --create-only

# Then post comprehensive demo as second comment
gh_pr=$(jq -r '.github.pr' .tmp/uat-run/last-run.json)
azdo_pr=$(jq -r '.azdo.pr' .tmp/uat-run/last-run.json)
scripts/uat-github.sh comment "$gh_pr" artifacts/comprehensive-demo-simple-diff.md
scripts/uat-azdo.sh comment "$azdo_pr" artifacts/comprehensive-demo.md

# Clean up when approved
scripts/uat-run.sh --cleanup-last
```

**GitHub** (`scripts/uat-github.sh`):
```bash
# Create PR and post markdown as comment
scripts/uat-github.sh create artifacts/<file>.md "<validation-description>"

# Post additional comment (for comprehensive demo)
scripts/uat-github.sh comment <pr-number> artifacts/<file>.md

# Poll for approval (exit 0 = approved, exit 1 = waiting)
scripts/uat-github.sh poll <pr-number>

# Clean up after approval
scripts/uat-github.sh cleanup <pr-number>
```

**Azure DevOps** (`scripts/uat-azdo.sh`):
```bash
# One-time setup (verifies auth, configures defaults)
scripts/uat-azdo.sh setup

# Create PR and post markdown as comment
scripts/uat-azdo.sh create artifacts/<file>.md "<validation-description>"

# Post additional comment (for comprehensive demo)
scripts/uat-azdo.sh comment <pr-id> artifacts/<file>.md

# Poll for approval (exit 0 = approved/resolved, exit 1 = waiting)
scripts/uat-azdo.sh poll <pr-id>

# Clean up after approval
scripts/uat-azdo.sh cleanup <pr-id>
```

#### Autonomous Polling Loop

After creating PRs, run polling automatically:
```bash
# Save original branch
ORIGINAL_BRANCH=$(git branch --show-current)

while true; do
    scripts/uat-github.sh poll "$GH_PR" && GH_OK=true
    scripts/uat-azdo.sh poll "$AZDO_PR" && AZDO_OK=true
    
    [[ "${GH_OK:-}" == "true" && "${AZDO_OK:-}" == "true" ]] && break
    sleep 15
done

# Cleanup and restore branch
scripts/uat-github.sh cleanup "$GH_PR"
scripts/uat-azdo.sh cleanup "$AZDO_PR"
git checkout "$ORIGINAL_BRANCH"
```

## Test Data

Tests use a shared test data file `TestData/azurerm-azuredevops-plan.json` containing a realistic Terraform plan with:

- Azure Resource Manager resources (resource group, storage account, key vault, virtual network)
- Azure DevOps resources (project, git repository)
- Various change actions (create, update, delete, replace)
- Sensitive values for testing masking behavior

Additional test data files for edge cases:

- `empty-plan.json` - Plan with no resource changes (empty `resource_changes` array)
- `no-op-plan.json` - Plan with only no-op changes (resources with no modifications)
- `minimal-plan.json` - Minimal valid plan with null before/after values
- `create-only-plan.json` - Plan with only create operations (new infrastructure deployment)
- `delete-only-plan.json` - Plan with only delete operations (infrastructure teardown)
- `firewall-rule-changes.json` - Firewall rule collection with semantic diff scenarios (add, modify, remove rules)
- `multi-module-plan.json` - Plan with multiple modules and nested modules to validate module grouping, ordering, and heading hierarchy

---

## Test Catalog

### CLI Parser Tests (`internal/cli/`)

Tests for command-line argument parsing logic using Go's `flag`/`cobra` parsing.

For user-facing changes (especially markdown rendering), run UAT in real environments using **temporary pull requests** in:

- GitHub PRs in `51nk0r5w1m/tfplan2md-uat`
- Azure DevOps PRs in `https://dev.azure.com/oocx` (project `test`, repository `test`)

The UAT loop is **comment-driven** and supports both approval and failure detection:

1. Create a UAT PR and post the generated markdown as a PR **comment**.
2. Maintainer reviews in the real PR UI and leaves feedback as PR comments/threads.
3. **Approval**: Maintainer comments with keywords like `approved`, `passed`, `lgtm`. The script detects this and exits successfully.
4. **Failure**: Maintainer comments with keywords like `fail`, `reject`, `error`, `bug`, `issue`, `regression`. The script detects this, stops polling, and exits with an error.
5. If failure is detected, apply fixes on the feature branch and re-run UAT (the script will create a new unique UAT branch and PR).

**Rules**:
- Do not close/abandon UAT PRs manually unless the script is stuck or Maintainer explicitly says **abort**.
- The script polls for new feedback until explicit approval or failure detection.

**Preferred: repo wrapper scripts (recommended)**

Use the stable wrapper scripts to minimize terminal approvals and to avoid brittle CLI output parsing:

```bash
# End-to-end UAT (creates PRs, posts comment(s), polls, and cleans up)
scripts/uat-run.sh run artifacts/<uat-file>.md

# Targeted GitHub operations
scripts/uat-github.sh create artifacts/<uat-file>.md
scripts/uat-github.sh poll <pr-number>
scripts/uat-github.sh comment <pr-number> artifacts/<uat-file>.md
scripts/uat-github.sh cleanup <pr-number>

# Targeted Azure DevOps operations
scripts/uat-azdo.sh setup
scripts/uat-azdo.sh create artifacts/<uat-file>.md
scripts/uat-azdo.sh poll <pr-id>
scripts/uat-azdo.sh comment <pr-id> artifacts/<uat-file>.md
scripts/uat-azdo.sh cleanup <pr-id>
```

**Manual fallbacks (only for debugging)**:

**GitHub (preferred in VS Code chat)**:
- Use GitHub chat tools to fetch PR conversation comments and review comments.

**GitHub (CLI fallback)**:
```bash
PAGER=cat gh pr view <pr-number> --comments
```

**Azure DevOps (threads via az devops invoke)**:
```bash
az account show >/dev/null || az login
az devops configure --defaults organization=https://dev.azure.com/oocx project=test

# Poll PR threads (repeat until approval/abort)
az devops invoke --area git --resource pullrequestthreads \
  --route-parameters project=test repositoryId=test pullRequestId=<pr-id> \
  --api-version 7.1
```

| Test Name | Description |
|-----------|-------------|
| `TestBuild_ValidPlan_ReturnsCorrectSummary` | Verifies that the summary correctly counts: 3 to add, 1 to change, 1 to destroy, 1 to replace, 6 total |
| `TestBuild_ValidPlan_ReturnsCorrectActionSymbols` | Verifies that action symbols are correctly assigned: `➕` for create, `🔄` for update, `❌` for delete, `♻️` for replace |
| `TestBuild_WithSensitiveValues_MasksByDefault` | Verifies that sensitive values are masked with "(sensitive)" by default |
| `TestBuild_WithShowSensitiveTrue_DoesNotMask` | Verifies that sensitive values are shown when `showSensitive` is true |
| `TestBuild_ValidPlan_PreservesTerraformVersion` | Verifies that Terraform and format versions are preserved in the model |
| `TestBuild_EmptyPlan_ReturnsZeroSummary` | Verifies that an empty plan returns zero counts for all summary fields |
| `TestBuild_NoOpPlan_CountsNoOpCorrectly` | Verifies that no-op resources are counted correctly in the summary |
| `TestBuild_MinimalPlan_HandlesNullBeforeAndAfter` | Verifies that plans with null before/after values produce empty attribute changes |
| `TestBuild_CreateOnlyPlan_CountsCreatesCorrectly` | Verifies that create-only plans are summarized correctly |
| `TestBuild_DeleteOnlyPlan_CountsDeletesCorrectly` | Verifies that delete-only plans are summarized correctly |

### Markdown Renderer Tests (`internal/markdown/`)

Tests for rendering the report model to Markdown output.

| Test Name | Description |
|-----------|-------------|
| `TestRender_ValidPlan_ContainsSummarySection` | Verifies that the rendered output contains a summary section with add/change/destroy indicators and emoji symbols |
| `TestRender_ValidPlan_ContainsResourceChanges` | Verifies that all resource addresses appear in the rendered output |
| `TestRender_ValidPlan_ContainsTerraformVersion` | Verifies that the Terraform version (1.14.0) appears in the rendered output |
| `TestRender_ValidPlan_ContainsActionSymbols` | Verifies that action symbols with resource addresses appear correctly (`➕`, `🔄`, `❌`, `♻️`) |
| `TestRender_EmptyPlan_ProducesValidMarkdown` | Verifies that an empty plan renders without errors and shows zero counts |
| `TestRender_NoOpPlan_ProducesValidMarkdown` | Verifies that a no-op plan renders correctly with the no-op action displayed |
| `TestRender_EmptyPlan_ShowsNoChangesMessage` | Verifies that an empty plan shows "No changes" message in the output |
| `TestRender_MinimalPlan_HandlesNullAttributes` | Verifies that resources with null before/after render without attribute details section |
| `TestRender_CreateOnlyPlan_ShowsAllCreates` | Verifies that create-only plans render all create operations with correct symbols |
| `TestRender_DeleteOnlyPlan_ShowsAllDeletes` | Verifies that delete-only plans render all delete operations with correct symbols |
| `TestRender_WithInvalidTemplate_ReturnsError` | Verifies that invalid template syntax returns a descriptive error |
| `TestRender_AttributeChangesTable_DoesNotContainExtraNewlines` | Verifies that attribute changes table rows are consecutive without blank lines |
| `TestRender_CreateOnlyPlan_ShowsAttributeValueTable` | Verifies that create-only plans render two-column `Attribute \| Value` tables showing after values |
| `TestRender_DeleteOnlyPlan_ShowsAttributeValueTable` | Verifies that delete-only plans render two-column `Attribute \| Value` tables showing before values |
| `TestRender_ReplacePlan_ShowsBeforeAndAfterColumns` | Verifies that replace operations (create+delete) render a 3-column `Attribute \| Before \| After` table |
| `TestRender_CreatePlan_MasksSensitiveAttributes` | Verifies that sensitive attributes are masked in the create `Value` column by default |
| `TestRender_Create_OmitsNullAndUnknownAttributes` | Verifies that null and unknown attributes are omitted from create tables |
| `TestRender_Delete_OmitsNullAttributes` | Verifies that null attributes are omitted from delete tables |
| `TestRenderResourceChange_FirewallRuleCollection_ReturnsResourceSpecificMarkdown` | Verifies that firewall rule collections use the resource-specific renderer |
| `TestRenderResourceChange_FirewallRuleCollection_ShowsAddedRules` | Verifies that added rules are shown with ➕ indicator |
| `TestRenderResourceChange_FirewallRuleCollection_ShowsModifiedRules` | Verifies that modified rules are shown with 🔄 indicator |
| `TestRenderResourceChange_FirewallRuleCollection_ShowsRemovedRules` | Verifies that removed rules are shown with ❌ indicator |
| `TestRender_MultiModulePlan_GroupsModulesAndPreservesOrder` | Verifies that plans with multiple and nested modules are grouped into module sections |
| `TestRender_MultiModulePlan_HeadingsAndHierarchyAreCorrect` | Verifies module headers use H3 and resources inside modules use H4 headings |
| `TestRender_FirewallModifiedRules_ShowsDiffForChangedAttributes` | Verifies that modified firewall rules show before/after diff format with `-` and `+` prefixes |

### Renderer Helper Tests (`internal/markdown/helpers/`)

Tests for the rendering helper functions used to produce diffs and formatted values.

| Test Name | Description |
|-----------|-------------|
| `TestDiffSlice_WithAddedItems_ReturnsAddedCollection` | Verifies that items present only in the after slice are returned as added |
| `TestDiffSlice_WithRemovedItems_ReturnsRemovedCollection` | Verifies that items present only in the before slice are returned as removed |
| `TestDiffSlice_WithModifiedItems_ReturnsModifiedCollectionWithBeforeAndAfter` | Verifies that items with changed values are returned with both before and after states |
| `TestDiffSlice_WithUnchangedItems_ReturnsUnchangedCollection` | Verifies that identical items are returned as unchanged |
| `TestDiffSlice_WithMixedChanges_ReturnsAllCategories` | Verifies that mixed add/remove/modify/unchanged scenarios are handled correctly |
| `TestDiffSlice_WithEmptyBeforeSlice_ReturnsAllAsAdded` | Verifies that all items are added when before slice is nil/empty |
| `TestDiffSlice_WithEmptyAfterSlice_ReturnsAllAsRemoved` | Verifies that all items are removed when after slice is nil/empty |
| `TestDiffSlice_WithMissingKeyField_ReturnsError` | Verifies that missing key field returns a descriptive error |
| `TestFormatDiff_EqualStrings_ReturnsSingleValue` | Verifies that equal before and after values return the value as-is without diff formatting |
| `TestFormatDiff_DifferentStrings_ReturnsDiffFormat` | Verifies that different values return `"- before<br>+ after"` format |
| `TestFormatDiff_NilBefore_ReturnsDiffFormat` | Verifies that nil before value is treated as empty string in diff format |
| `TestFormatDiff_NilAfter_ReturnsDiffFormat` | Verifies that nil after value is treated as empty string in diff format |
| `TestFormatDiff_BothNil_ReturnsEmptyString` | Verifies that both nil values return empty string |

### Docker Integration Tests (`test/integration/`)

End-to-end integration tests that run the application in a Docker container. Tagged with `//go:build integration` and skipped when Docker is unavailable.

| Test Name | Description |
|-----------|-------------|
| `TestDocker_WithFileInput_ProducesMarkdownOutput` | Verifies that the container correctly processes a plan file mounted as a volume and produces valid Markdown output |
| `TestDocker_WithStdinInput_ProducesMarkdownOutput` | Verifies that the container correctly processes plan JSON from stdin and produces valid Markdown output |
| `TestDocker_WithHelpFlag_DisplaysHelp` | Verifies that the `--help` flag displays usage information in the container |
| `TestDocker_WithVersionFlag_DisplaysVersion` | Verifies that the `--version` flag displays version information in the container |
| `TestDocker_WithInvalidInput_ReturnsNonZeroExitCode` | Verifies that invalid JSON input results in a non-zero exit code and error message |

### Markdown Lint Integration Tests (`test/integration/`)

Docker-based integration tests that run the actual markdownlint-cli2 tool to validate markdown output. Use the `davidanson/markdownlint-cli2` Docker image for consistent validation.

| Test Name | Description |
|-----------|-------------|
| `TestLint_ComprehensiveDemo_PassesAllRules` | Verifies the comprehensive demo output passes all markdownlint rules |
| `TestLint_AllTestPlans_PassAllRules` | Verifies all test plans in testdata produce valid markdown |
| `TestLint_SummaryTemplate_PassesAllRules` | Verifies the summary template produces valid markdown |

### Markdown Invariant Tests (`internal/markdown/`)

Table-driven tests that verify markdown invariants that must ALWAYS hold, regardless of input.

| Test Name | Description |
|-----------|-------------|
| `TestInvariant_NoConsecutiveBlankLines` | MD012: Verifies no plan produces more than one consecutive blank line |
| `TestInvariant_AllTablesParseable` | Verifies all tables parse correctly |
| `TestInvariant_NoBlankLinesBetweenTableRows` | Verifies table rows are consecutive without blank lines |
| `TestInvariant_NoRawNewlinesInTableCells` | Verifies no raw newlines exist inside table cells |
| `TestInvariant_PipesEscapedInTableCells` | Verifies pipes are escaped in table cells |
| `TestInvariant_HeadingsSurroundedByBlankLines` | Verifies headings have proper spacing |
| `TestInvariant_DetailsTagsBalanced` | Verifies all `<details>` tags are properly closed |
| `TestInvariant_HasTerraformPlanHeading` | Verifies every plan has a Terraform Plan heading |
| `TestInvariant_HasSummarySection_NonEmptyPlans` | Verifies non-empty plans have a Summary section |

### Markdown Snapshot Tests (`internal/markdown/`)

Golden file tests that detect unexpected changes in markdown output by comparing against approved baselines stored in `testdata/snapshots/`.

| Test Name | Description |
|-----------|-------------|
| `TestSnapshot_ComprehensiveDemo_MatchesBaseline` | Verifies comprehensive demo matches stored snapshot |
| `TestSnapshot_SummaryTemplate_MatchesBaseline` | Verifies summary template matches stored snapshot |
| `TestSnapshot_FirewallRules_MatchesBaseline` | Verifies firewall rule rendering matches stored snapshot |
| `TestSnapshot_MultiModule_MatchesBaseline` | Verifies multi-module plan matches stored snapshot |

### Fuzz Tests (`internal/markdown/`, `internal/parsing/`)

Fuzz testing with random/edge-case inputs using Go's built-in `testing/fuzz`.

```bash
# Run fuzz tests (in src-go/)
go test ./internal/markdown/... -fuzz=FuzzRender -fuzztime=60s
go test ./internal/parsing/... -fuzz=FuzzParsePlan -fuzztime=60s
```

| Fuzz Target | Description |
|-------------|-------------|
| `FuzzRender` | Fuzz markdown rendering with arbitrary plan inputs |
| `FuzzParsePlan` | Fuzz plan JSON parsing with arbitrary byte sequences |
| `FuzzEscapeMarkdown` | Fuzz markdown escaping with arbitrary strings |

### Style Guide Compliance Tests (`internal/markdown/`)

Automated validation of generated markdown against the [Report Style Guide](report-style-guide.md). These tests scan all snapshot files to detect style guide violations.

**Running Compliance Tests:**
```bash
go test -run TestStyleGuide ./internal/markdown/...
go test -run TestStyleGuide/AzApiResourceNames ./internal/markdown/...
```

| Test Name | Description |
|-----------|-------------|
| `TestStyleGuide/AzApiResourceNames_NotEmpty` | Detects empty `<b></b>` tags in resource summaries (high severity) |
| `TestStyleGuide/WrenchIcon_HasNonBreakingSpace` | Validates non-breaking space before 🔧 icon in changed attribute summaries |
| `TestStyleGuide/TagsHeader_HasIcon` | Ensures tags headers include 🏷️ emoji per style guide |
| `TestStyleGuide/ModuleHeaders_HavePackageIcon` | Validates 📦 icon in module headers |
| `TestStyleGuide/NoH3HeadingsInDetails` | Prevents H3 headings inside `<details>` blocks |
| `TestStyleGuide/AttributeNamesNotInBackticks` | Ensures attribute names are plain text, not code-formatted |

**How These Tests Work:**

1. **Scan all snapshot files** - Tests examine every `.golden.md` file in `testdata/snapshots/`
2. **Pattern-based detection** - Use `regexp` patterns to find style guide violations
3. **Generic validation** - Not tied to specific resources; works across all templates and providers
4. **Clear error messages** - Report exact violation locations and expected patterns

**When Tests Fail:**

1. Review the error message — shows which files violate which style guide rule
2. Check [docs/report-style-guide.md](report-style-guide.md) — understand the violated rule
3. Fix the implementation:
   - Update Go template strings in `internal/markdown/templates/` or `internal/providers/{name}/templates/`
   - Update helper functions in `internal/markdown/helpers/`
4. Regenerate test snapshots if the fix changes expected output
5. Re-run compliance tests to verify the fix

**Benefits:**

- **Prevents regressions** — New templates must pass style guide checks
- **Automated validation** — No manual verification needed
- **Consistency enforcement** — All generated markdown follows same standards
- **Documentation as tests** — Tests serve as executable specification of the style guide