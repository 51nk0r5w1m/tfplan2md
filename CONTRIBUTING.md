# Contributing to tfplan2md

Thank you for your interest in contributing to tfplan2md! This document provides guidelines and instructions for contributing.

## Development Workflow

### Branch Strategy

1. **Main branch** (`main`) — Always in a releasable state
2. **Feature branches** — Created from `main` for new features or fixes

### Creating a Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feat/your-feature-name
```

Use these branch prefixes:
- `feat/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation changes
- `refactor/` — Code refactoring
- `chore/` — Maintenance tasks
- `workflow/` — Agent/workflow changes (`.github/agents/`, workflow documentation)
- `website/` — Website changes (`website/` directory)

## Testing Requirements

All changes must include appropriate tests. The project uses a comprehensive testing strategy:

### Test Types

1. **Unit Tests** - Test individual Go packages in isolation using `go test` and `testify/assert`
2. **Integration Tests** - Test end-to-end workflows, including Docker-based tests
3. **Table-Driven Tests** - Go idiomatic test pattern using `t.Run` subtests for input/output coverage
4. **Snapshot Tests** - Golden file tests that detect unexpected output changes (compare generated markdown against expected `.md` files)
5. **Fuzz Tests** - Test with edge-case inputs using Go's built-in `testing/fuzz` (`go test -fuzz=FuzzXxx`)
6. **Markdownlint Integration** - Docker-based linting with actual markdownlint-cli2
7. **Race Detection** - All tests run with `-race` flag in CI to detect data races

### Running Tests

```bash
# Run all tests (from src-go/)
go test ./...

# Run tests with race detector (required in CI)
go test -race ./...

# Run tests with coverage
go test -race -coverprofile=coverage.out ./...
go tool cover -html=coverage.out  # view in browser

# Run a specific package
go test ./internal/parsing/...

# Run a specific test by name
go test ./internal/parsing/... -run TestResourceChangeActions

# Run table-driven subtests
go test ./internal/markdown/... -run TestRender/create_resource

# Run fuzz tests (from src-go/)
go test ./internal/parsing/... -fuzz=FuzzParsePlan -fuzztime=30s

# Run with verbose output
go test -v ./...

# Use the timeout wrapper (preferred for CI and long-running tests)
scripts/test-with-timeout.sh -- go test -race ./...
```

### Architecture Rules

The Go codebase follows strict package dependency rules enforced by `golangci-lint` import analysis:

**Key package dependency rules:**

- `internal/parsing` must NOT import `internal/markdown` (prevents circular dependencies)
- `internal/markdown` must NOT import `internal/providers` (general rendering independent of specific providers)
- `cmd/` packages may import `internal/` packages but not vice versa
- All implementation lives in `internal/` — no package outside this module can import it

**If you introduce a dependency violation:**
1. Check `golangci-lint run ./...` output for import cycle errors
2. Refactor by introducing an interface in a shared `internal/` package
3. Move shared types to a lower-level package that both can import

See [docs/architecture-rules.md](docs/architecture-rules.md) for complete layer definitions.

### Markdown Quality Requirements

All generated markdown must:
- Pass markdownlint validation (MD012 and other rules)
- Render correctly on GitHub, Azure DevOps, and Bitbucket
- Have proper table structure (no blank lines between rows)
- Have proper heading spacing (blank lines before/after)
- Have balanced HTML tags (`<details>`, `<summary>`)

See [docs/testing-strategy.md](docs/testing-strategy.md) for complete testing documentation.

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) to automate versioning and changelog generation.

### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | A new feature | Minor (0.x.0) |
| `fix` | A bug fix | Patch (0.0.x) |
| `docs` | Documentation only changes | None |
| `style` | Code style changes (formatting, etc.) | None |
| `refactor` | Code refactoring without feature changes | None |
| `perf` | Performance improvements | Patch (0.0.x) |
| `test` | Adding or modifying tests | None |
| `build` | Build system or dependency changes | None |
| `ci` | CI configuration changes | None |
| `chore` | Other maintenance tasks | None |
| `workflow` | Agent/workflow changes (`.github/agents/`, `docs/agents.md`) | None |
| `revert` | Reverting a previous commit | Depends |

### Breaking Changes

For breaking changes, add `BREAKING CHANGE:` in the commit footer:

```
feat(parser): change output format to JSON

BREAKING CHANGE: The output format has changed from plain text to JSON.
```

Or use `!` after the type:

```
feat(parser)!: change output format to JSON
```

Breaking changes trigger a **major** version bump (x.0.0).

### Commit Cohesion

**Each commit should focus on a single topic or change.**

- ✅ High cohesion: One commit for fixing a bug, another for refactoring tests
- ❌ Low cohesion: One commit that fixes a bug AND refactors tests AND updates documentation

**Why:** Focused commits make it easier to:
- Understand what changed and why
- Review changes effectively
- Revert specific changes if needed
- Track down bugs with `git bisect`

If you find yourself using "and" repeatedly in a commit message, consider splitting it into multiple commits.

### Examples

```bash
# Feature
git commit -m "feat(cli): add --output flag for custom output path"

# Bug fix
git commit -m "fix(parser): handle empty resource changes array"

# Documentation
git commit -m "docs: update installation instructions"

# Workflow changes
git commit -m "workflow: update Task Planner agent model"

# Breaking change
git commit -m "feat(api)!: rename TerraformPlan to PlanResult"
```

## Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** following the coding guidelines
3. **Ensure all checks pass**:
   ```bash
   # From src-go/
   gofmt -l ./...          # check formatting (no output = clean)
   go vet ./...            # static analysis
   go build ./...          # build
   go test -race ./...     # tests with race detector
   golangci-lint run ./... # full lint
   ```
4. **Push your branch** and create a Pull Request
5. **Wait for review** — PR validation will run automatically
6. **Merge using "Rebase and merge"** — This project requires a linear history

### PR Requirements

- All CI checks must pass (build, test, format, vulnerability scan)
- Code follows the project's style guidelines (enforced by `.editorconfig`)
- Commit messages follow Conventional Commits format

### Merge Strategy

**This project uses rebase and merge to maintain a linear Git history.**

- When merging a PR, use the "Rebase and merge" button
- If "Rebase and merge" is not available due to conflicts:
  1. Update your branch by rebasing onto main: `git pull --rebase origin main`
  2. Resolve any conflicts
  3. Force-push your branch: `git push --force-with-lease`
  4. The PR will then be ready to merge
- Do NOT use "Squash and merge" or "Create a merge commit"

## Coding Standards

### Code Quality Metrics

This project enforces automated code quality metrics via `golangci-lint` to ensure maintainable, readable code:

- **Cyclomatic Complexity** (`gocyclo`/`cyclop`): Maximum 15 per function
- **Function Length** (`funlen`): Maximum ~80 lines per function
- **Line Length**: Maximum 160 characters
- **File Length**: Target ~300 lines per file (guideline)

These metrics are enforced at CI time via `golangci-lint` and will cause PR validation failures if violated. Configuration is in `.golangci.yml`.

**Suppression Policy:**

Suppressions are allowed only when refactoring would harm readability or maintainability. Requirements:

1. Use `//nolint:lintername` inline comment with a justification
2. Add a comment above the suppressed line/block explaining why suppression is necessary
3. Reference related feature/task documentation if applicable
4. Obtain maintainer approval in the PR review

Example:
```go
// Complex state machine requires > 15 branches for RFC compliance.
// Approved by maintainer in PR #346.
//nolint:cyclop // RFC 9110 HTTP semantics require explicit handling of each status class
func processRequest(req *http.Request) httpStatus {
    // implementation
}
```

See [docs/commenting-guidelines.md](docs/commenting-guidelines.md) for complete suppression guidelines.

### Package Visibility

`tfplan2md` is a standalone CLI tool. Use Go's visibility conventions:

- ✅ Unexported (`camelCase`) — default for all implementation details
- ✅ Exported (`PascalCase`) — only when needed across package boundaries
- ⚠️ All implementation lives in `internal/` — enforced by Go toolchain; no external imports possible

**Never export identifiers just for testing.** Instead, use same-package `_test.go` files to access unexported identifiers.

**Why:** This prevents false concerns about API backwards compatibility, since there are no external consumers of the code.

### Code Comments

All code must be thoroughly documented following [docs/commenting-guidelines.md](docs/commenting-guidelines.md):

- **All exported identifiers** require Go doc comments (start with `// IdentifierName ...`)
- **Unexported identifiers** should have comments when purpose is not immediately obvious
- Comments must explain **"why"** not just **"what"**
- Reference related features/specifications for traceability
- Keep comments synchronized with code changes

Examples:

```go
// ParsePlan reads a Terraform plan JSON file and returns the parsed plan.
// It uses streaming JSON decoding to handle large plan files efficiently.
// Related feature: docs/features/008-comprehensive-demo/
func ParsePlan(path string) (*Plan, error) {
    // implementation
}
```

See [docs/commenting-guidelines.md](docs/commenting-guidelines.md) for complete guidelines.

## Project Structure

Understanding the codebase organization will help you navigate and contribute effectively.

### High-Level Organization

```
tfplan2md/
├── src-go/                              # Go implementation
│   ├── cmd/tfplan2md/                   # Entry point (main.go)
│   ├── internal/
│   │   ├── cli/                         # Command-line parsing (cobra)
│   │   ├── parsing/                     # Terraform plan JSON parsing
│   │   ├── markdown/                    # Core report building and rendering
│   │   ├── providers/                   # Provider-specific logic (azurerm, azapi, azuredevops)
│   │   ├── rendertargets/               # Platform-specific formatting (GitHub, Azure DevOps)
│   │   └── platforms/                   # Cloud platform utilities (Azure)
│   ├── testdata/                        # Shared test fixtures (plan JSON + expected snapshots)
│   ├── go.mod
│   └── go.sum
└── docs/                                # Documentation
```

### Provider Architecture

Terraform provider-specific code (azurerm, azapi, azuredevops) is organized into modular provider packages under `src-go/internal/providers/`:

Each provider implements the `Provider` interface:
- **Attribute filters**: Which JSON attributes to include/exclude
- **Value formatters**: How to display specific attribute values
- **Icon rules**: Embedded JSON loaded via `//go:embed` for resource-type icons

**Adding a new provider?** Create a new package under `internal/providers/<name>/`, implement the `Provider` interface, and register it in `internal/providers/registry.go`.

### Core Components

| Component | Path | Purpose |
|-----------|------|---------|
| **CLI** | `internal/cli/` | Command-line parsing and orchestration |
| **Parsing** | `internal/parsing/` | Terraform plan JSON deserialization |
| **Markdown** | `internal/markdown/` | Core report building and rendering |
| **Providers** | `internal/providers/{name}/` | Provider-specific logic (azurerm, azapi, azuredevops) |
| **RenderTargets** | `internal/rendertargets/` | Platform-specific diff formatting (GitHub, Azure DevOps, Bitbucket) |
| **Platforms** | `internal/platforms/azure/` | Azure-specific utilities (principal mapping, role names) |

### Architecture Documentation

For comprehensive architecture details, see:
- [docs/architecture.md](docs/architecture.md) - Full arc42 architecture documentation
- [docs/spec.md](docs/spec.md) - Project specification and technical details

## Local Development Setup

### Prerequisites

- [Go 1.22+](https://go.dev/dl/)
- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/) (for running integration tests)
- [golangci-lint](https://golangci-lint.run/usage/install/) (for local linting)
- **Shell tools**: Keep release scripts POSIX-compatible; avoid GNU awk-only extensions (e.g., function-local params, match capture arrays). Use `POSIXLY_CORRECT=1` when testing shell changes locally.

### Getting Started

```bash
# Clone the repository
git clone https://github.com/51nk0r5w1m/tfplan2md.git
cd tfplan2md/src-go

# Download module dependencies
go mod download

# Install git hooks (commit-msg validation)
cp scripts/hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg

# Build and test
go build ./...
go test -race ./...
```

### Pre-commit Hooks

This project uses shell-based git hooks for quality gates:

- **pre-commit**: Runs `gofmt -l ./...` and `go vet ./...`
- **commit-msg**: Validates commit message follows Conventional Commits format

If your commit is rejected:
1. **Format issues**: Run `gofmt -w ./...` and `goimports -w ./...` to fix formatting
2. **Vet errors**: Fix the reported issues before committing
3. **Commit message**: Ensure your message follows the format `type: description`

## Maintaining Azure API Documentation Mappings

The AzAPI provider includes curated mappings between Azure resource types and their official REST API documentation URLs. These mappings ensure users get reliable documentation links instead of broken heuristic guesses.

### When to Update Mappings

Update the mappings when:
- A user reports a broken or missing documentation link
- Microsoft launches a new Azure service or resource type
- Microsoft restructures documentation URLs (rare but possible)
- Regular maintenance (maintainer's discretion based on Azure releases)

### Update Process

**Prerequisites:**
- Python 3.7 or later
- Internet connection (script scrapes Microsoft Learn)

**Steps:**

1. **Run the discovery script:**
   ```bash
   python3 scripts/update-azure-api-mappings.py
   ```
   This generates updated mappings by scraping the Azure SDK Specs Inventory page and saves them to `src/Oocx.TfPlan2Md/Providers/AzApi/Data/AzureApiDocumentationMappings.json`.

2. **Spot-check the output:**
   - Review the generated JSON file
   - Check the `totalMappings` count in metadata (should be 90+)
   - Verify a few sample URLs manually:
     ```bash
     # Example: Check a few URLs
     cat src/Oocx.TfPlan2Md/Providers/AzApi/Data/AzureApiDocumentationMappings.json | \
       jq '.mappings | to_entries | .[0:3] | .[] | .key + " -> " + .value.url'
     ```

3. **Validate URLs (optional):**
   ```bash
   # Warning: This is slow (makes HTTP requests for each URL)
   python3 scripts/update-azure-api-mappings.py --validate
   ```
   Only use `--validate` when you need to verify URL correctness. It's not recommended for routine updates.

4. **Test the changes:**
   ```bash
   go build ./...
   go test -race ./...
   ```

5. **Commit the updated mappings:**
   ```bash
   git add src-go/internal/providers/azapi/data/AzureApiDocumentationMappings.json
   git commit -m "chore: update Azure API documentation mappings"
   ```

### Script Options

The `update-azure-api-mappings.py` script supports the following options:

- `--output PATH` - Custom output file path (default: `src/Oocx.TfPlan2Md/Providers/AzApi/Data/AzureApiDocumentationMappings.json`)
- `--validate` - Validate all URLs by making HTTP HEAD requests (slow, not recommended for routine use)
- `--help` - Show help message

### Mapping File Format

The mappings are stored in JSON format:

```json
{
  "mappings": {
    "Microsoft.Compute/virtualMachines": {
      "url": "https://learn.microsoft.com/rest/api/compute/virtual-machines"
    },
    "Microsoft.Storage/storageAccounts": {
      "url": "https://learn.microsoft.com/rest/api/storagerp/storage-accounts"
    }
  },
  "metadata": {
    "version": "1.0.0",
    "lastUpdated": "YYYY-MM-DD",
    "source": "Microsoft Learn REST API Documentation (manually curated)",
    "generatedBy": "scripts/update-azure-api-mappings.py",
    "totalMappings": 92
  }
}
```

**Key points:**
- Resource types are **version-agnostic** (no `@YYYY-MM-DD` suffix)
- Nested resources have individual mappings (e.g., `Microsoft.Storage/storageAccounts/blobServices`)
- URLs point to Microsoft Learn REST API documentation

### Related Documentation

- Feature specification: [docs/features/048-azure-api-doc-mapping/specification.md](docs/features/048-azure-api-doc-mapping/specification.md)
- Architecture design: [docs/features/048-azure-api-doc-mapping/architecture.md](docs/features/048-azure-api-doc-mapping/architecture.md)

## Maintaining Microsoft Graph App Role Mappings

The Azure AD provider resolves Microsoft Graph application-permission GUIDs (e.g., `app_role_id` on `azuread_app_role_assignment`) to human-readable names (e.g., `Policy.ReadWrite.Authorization`) using the embedded mapping at `src/Oocx.TfPlan2Md/Platforms/Azure/MicrosoftGraphAppRoles.json`. The mapping is regenerated from the upstream source of the [Microsoft Graph permissions reference](https://learn.microsoft.com/graph/permissions-reference) (the `microsoftgraph/microsoft-graph-docs-contrib` markdown that the Learn page is built from).

**Scope:** Microsoft Graph **application** permissions only. Delegated `oauth2PermissionScopes` GUIDs and non-Graph APIs (SharePoint, Exchange, Office 365, Intune, Azure Service Management, etc.) are intentionally out of scope.

### When to Update Mappings

Update the mappings when:
- A user reports a well-known Microsoft Graph app permission GUID that renders as a raw GUID instead of its friendly name
- Microsoft adds new Graph application permissions
- Regular maintenance (maintainer's discretion)

### Update Process

**Prerequisites:**
- Python 3.7 or later (standard library only)
- Internet connection (script fetches the upstream markdown from GitHub)

**Steps:**

1. **Run the regeneration script:**
   ```bash
   python3 scripts/update-msgraph-app-roles.py
   ```
   This downloads the upstream permissions reference markdown, extracts every well-known Microsoft Graph application permission GUID, and writes the sorted `{guid: name}` mapping to `src/Oocx.TfPlan2Md/Platforms/Azure/MicrosoftGraphAppRoles.json`. The script prints an added/removed/total summary on each run and is idempotent.

2. **Preview without writing:**
   ```bash
   python3 scripts/update-msgraph-app-roles.py --dry-run
   ```

3. **Use a custom source or output path** (e.g., for offline regeneration from a local checkout of the docs repo):
   ```bash
   python3 scripts/update-msgraph-app-roles.py \
     --source /path/to/permissions-reference.md \
     --output src/Oocx.TfPlan2Md/Platforms/Azure/MicrosoftGraphAppRoles.json
   ```

4. **Test the changes:**
   ```bash
   go build ./...
   go test -race ./...
   ```

5. **Commit the updated mappings:**
   ```bash
   git add src-go/internal/platforms/azure/MicrosoftGraphAppRoles.json
   git commit -m "chore: update Microsoft Graph app role mappings"
   ```

### Script Options

The `update-msgraph-app-roles.py` script supports the following options:

- `--source URL_OR_PATH` — Override the upstream markdown source (default: the raw `microsoftgraph/microsoft-graph-docs-contrib` permissions reference)
- `--output PATH` — Custom output file path (default: `src/Oocx.TfPlan2Md/Platforms/Azure/MicrosoftGraphAppRoles.json`)
- `--dry-run` — Print the added/removed/total summary without writing the file
- `--help` — Show help message

### Mapping File Format

The mappings are stored as a flat sorted `{guid: name}` JSON object so that `MicrosoftGraphAppRolesRegistry` can load them as a `FrozenDictionary`:

```json
{
  "fb221be6-99f2-473f-bd32-01c6a0e9ca3b": "Policy.ReadWrite.Authorization",
  "df021288-bdef-4463-88db-98f22de89214": "User.Read.All"
}
```

GUIDs are sorted lexicographically for deterministic diffs across regenerations.

## Release Process

Releases are automated via GitHub Actions:

1. When commits are pushed to `main`, the CI workflow runs Versionize
2. Versionize only runs when Docker-relevant files changed (runtime code, examples, build config)
3. If there are `feat:`, `fix:`, or `BREAKING CHANGE` commits, Versionize:
   - Bumps the version in `go.mod` (or a dedicated version file)
   - Updates `CHANGELOG.md`
   - Creates a git tag (e.g., `v0.2.0`)
4. The tag push triggers the Release workflow which:
   - Looks for user-focused release notes in `docs/features/NNN-<feature-slug>/release-notes.md`
   - If found, uses those notes for the GitHub Release (blog-post style, user-facing)
   - Otherwise, falls back to extracting notes from `CHANGELOG.md`
   - Builds and pushes the Docker image to Docker Hub
   - Builds pre-built binaries for all six supported platforms (linux-x64, linux-arm64, linux-musl-x64, linux-musl-arm64, macos-arm64, windows-x64) and uploads them as release assets alongside a `SHA256SUMS` checksum file

### Release Notes

The Release Manager agent creates user-focused release notes in blog-post style:
- **Location**: `docs/features/NNN-<feature-slug>/release-notes.md`
- **Style**: Written for end-users, not developers
- **Content**: Features and improvements users can see, excluding internal commits
- **Format**: Compelling overview, code examples, practical use cases
- **Filters out**: Task tracking commits, documentation updates, workflow changes

**Note:** Changes to tests, documentation, website, scripts, or GitHub workflows do not trigger releases, as they don't affect the published Docker image.

## Questions?

If you have questions, feel free to open an issue for discussion.
