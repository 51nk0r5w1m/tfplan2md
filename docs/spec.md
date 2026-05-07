# Project specification

## Project Overview
`tfplan2md` is a CLI tool that converts Terraform plan JSON files into human-readable markdown reports. It is built using **Go 1.22+**, emphasizing clean architecture, testability, and maintainability.

The goal of this tool is to help DevOps and infrastructure teams easily review Terraform plans by generating concise markdown summaries of proposed changes. The tool produces a static, cross-platform binary distributed via Docker, GitHub Releases, and Homebrew.

## Project Organization
- Use Go packages to organize the code. The module path is `github.com/51nk0r5w1m/tfplan2md`
- Go source lives under `src-go/` with standard layout: `cmd/tfplan2md/` (entry point), `internal/` (all implementation packages)
- Organize packages by feature (e.g., `internal/parsing`, `internal/markdown`, `internal/cli`, `internal/providers`), not by type (e.g., `models`, `services`)
- Place all documentation in the /docs folder, except for the README.md at the root
- Key architecture decisions must be documented in separate files per decision. Place those files in /docs/adr-nnn-title.
- Documentation subfolders under `/docs/features`, `/docs/issues`, and `/docs/workflow` use a global numeric prefix: `NNN-<topic-slug>`.
  - **Parallel work rule:** If two branches chose the same next `NNN`, the first PR to merge keeps it; later PRs must renumber before merge.
- The testing strategy is described in /docs/testing-strategy.md
- Features of tfplan2md (from a user perspective) are described in /docs/features.md
- Contribution guidelines are in /CONTRIBUTING.md

## Coding Standards

### Package Visibility

**This is NOT a library** — `tfplan2md` is a standalone CLI tool. Use Go's package visibility conventions appropriately:

- **Prefer unexported identifiers** (`camelCase`) for all implementation details within a package
- **Export (`PascalCase`) only when** an identifier must be referenced from another package
- All implementation code lives in `internal/` sub-packages, which Go enforces as non-importable by external modules
- The `cmd/tfplan2md/main.go` entry point is the only exported surface

- **Test Access Strategy:**
  - Use `_test.go` files in the same package (white-box tests) to access unexported identifiers
  - Use separate `_test` package suffix (e.g., `package parsing_test`) for black-box integration tests
  - Do NOT export identifiers solely for testing — use same-package tests instead

- **Why this matters:**
  - Keeping identifiers unexported makes clear they are implementation details
  - `internal/` packages are enforced by the Go toolchain — no external consumers possible
  - This prevents false concerns about API stability and breaking changes

### Code Comments

- **All exported identifiers must have Go doc comments** (e.g., `// TypeName does ...`)
- **Unexported identifiers** should have comments when the purpose is not immediately obvious
- Comments should explain "why" something was done, not just repeat what the code shows
- Follow the comprehensive guidelines in [docs/commenting-guidelines.md](commenting-guidelines.md)
- Key requirements:
  - Go doc comments are plain text starting with `// FunctionName ...` or `// PackageName ...`
  - `// Deprecated:` prefix marks deprecated identifiers
  - Reference related features/specifications for traceability
  - Keep comments synchronized with code changes

## CI/CD and Versioning

### Versioning Strategy
- Use [Semantic Versioning](https://semver.org/) (SemVer)
- Automate versioning with [Versionize](https://github.com/versionize/versionize) based on [Conventional Commits](https://www.conventionalcommits.org/)
- Version tags use `v` prefix (e.g., `v1.0.0`)
- Docker images are tagged with full version. Stable releases also include minor version, major version, and `latest` tags.

### Commit Message Format
- Follow [Conventional Commits](https://www.conventionalcommits.org/) specification
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Breaking changes: Use `BREAKING CHANGE:` footer or `!` after type
- Pre-commit hooks enforce commit message format

### GitHub Actions Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|----------|
| PR Validation | `pr-validation.yml` | Pull requests to `main` | Format check (`gofmt`), build (`go build`), test (`go test`), markdown lint, vulnerability scan (`govulncheck`) |
| CI | `ci.yml` | Push to `main` | Run Versionize to bump version and create tag **only when Docker-relevant files changed** (tests run in PR Validation) |
| Release | `release.yml` | Version tags (`v*`) | Create GitHub Release with cumulative changelog, cross-compile Go binaries, build and push Docker image |
| CodeQL | _(default setup)_ | Push/PR to `main`, weekly schedule | Static analysis security scanning (Go source code) — managed by GitHub's CodeQL default setup |

**Test Optimization:** Tests only run in PR Validation workflow to eliminate redundancy. CI workflow focuses solely on versioning after merge, significantly reducing CI time. All quality gates (format, build, test, lint, vulnerability scan) must pass in PR validation before merge.

**Release Gating:** The CI workflow only creates a new version tag when the published Docker image would change. This includes changes to runtime code (`src-go/` excluding test files), example files (`examples/`), and Docker build configuration. Test-only changes and workflow/internal-tooling changes (`.github/`, `scripts/`, `docs/`, `website/`) intentionally do not trigger releases.

**Commit Guardrails:** Pull requests that only change workflow/internal tooling (e.g., `.github/`, `scripts/`, `docs/`, `website/`) must not use version-bumping Conventional Commit types such as `feat:` or `fix:`. Use `workflow:`, `docs:`, `chore:`, or `ci:` instead. **Why:** Versionize treats `feat:` as a minor bump and `fix:` as a patch bump. Incorrect commit types cause unintended version increments (e.g., a minor bump instead of a patch, or a release for changes that don't affect the published Docker image). The Release Manager agent must verify commit types before merging.

**Release Notes:** The release workflow generates cumulative release notes that include all changes since the last GitHub release. This ensures Docker deployments contain complete change history even when intermediate versions are not released.

### Code Quality
- **Linter**: `golangci-lint` with `staticcheck`, `errcheck`, `gosimple`, `govet`, `ineffassign`, `unused` enabled; treat all warnings as errors in CI
- **Code Metrics**: `golangci-lint` enforces cyclomatic complexity (≤15 via `gocyclo`/`cyclop`), file length (~300 lines), and function length
- **Code Style**: Enforced via `gofmt` and `goimports`; `.editorconfig` set for Go tab indentation
- **Architecture Enforcement**: Package structure enforced via `go vet` and `golangci-lint` rules; `internal/` packages enforced by the Go toolchain
- **Pre-commit Hooks**: Git hooks (via shell scripts in `.git/hooks/` or `pre-commit` framework) run `gofmt -l` and `go vet ./...` before commit
- **Dependency Updates**: Dependabot configured for Go modules (`go.mod`/`go.sum`), Docker, and GitHub Actions
- **Suppression Policy**: Linter suppressions (`//nolint:lintername`) require inline justification comment and maintainer approval (see [docs/commenting-guidelines.md](commenting-guidelines.md))
- **Vulnerability Scanning**: `govulncheck ./...` runs in PR Validation to detect known Go module vulnerabilities

### Branch Strategy
- `main` branch is always in a releasable state
- Feature branches created from `main` for new features or fixes
- Pull requests require passing validation checks before merge

**Branch Protection Limitation (Private Repos):**
- GitHub branch protection rules (requiring status checks) require GitHub Pro for private repositories
- Until the repository is made public, PRs CAN be merged before the "PR Validation" workflow completes
- **CRITICAL**: Agents and maintainers must manually verify "PR Validation" shows ✅ success before merging
- The Release Manager agent enforces this requirement by monitoring PR status checks (prefer GitHub chat tools; `gh pr checks --watch` is a fallback)
- Once the repository is public, configure branch protection to require the "PR Validation" workflow as a required status check
