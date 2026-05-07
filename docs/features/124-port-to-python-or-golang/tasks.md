# Tasks: Port tfplan2md to Golang

## Overview

Port the existing `tfplan2md` CLI tool to **Golang**.
The tool converts Terraform plan JSON files into human-readable Markdown reports.

**Language decision:** Golang — confirmed by Maintainer. Produces a self-contained static
binary compatible with scratch Docker containers, cross-compiles trivially to all target
platforms, and closely matches the current NativeAOT distribution model.

> ⚠️ **Prerequisites Missing**: This feature was submitted directly to the Task Planner without
> passing through the Requirements Engineer or Architect phases. A formal specification and
> architecture document have not been created. The open questions section at the bottom captures
> remaining decisions that must be resolved before or during implementation.

---

## Tasks

### Task 1: Golang Architecture Decision Record

**Priority:** High (Blocker — must be completed before Tasks 3–12)

**Description:**
Document the confirmed Golang port decision in an ADR. This establishes the authoritative
record for the language choice and defines the key Go conventions and constraints that all
subsequent tasks must follow (module path, minimum Go version, linter configuration, etc.).

**Acceptance Criteria:**
- [ ] ADR created at `docs/adr-012-port-to-golang.md` (follows the `adr-NNN-<slug>.md` naming convention; next after `adr-011-upx-binary-compression.md`)
- [ ] ADR covers: context, decision (Golang), rationale, key Go-ecosystem choices (JSON library,
  CLI library, test framework), and consequences for distribution and CI
- [ ] Minimum Go version documented (recommend Go 1.22+ for `range` over integers, `slices`/`maps` packages)
- [ ] Go module path decided and documented (e.g., `github.com/51nk0r5w1m/tfplan2md`)
- [ ] ADR reviewed and merged before implementation starts

**Dependencies:** None

**Notes:**
The Golang choice was confirmed by the Maintainer. The ADR should not re-open the language
debate but should document the Go-specific design constraints and tool choices.

---

### Task 2: Formal Specification and Architecture Document

**Priority:** High (Blocker — must be completed before Tasks 3–11)

**Description:**
Create the missing specification (`specification.md`) and architecture (`architecture.md`) for
this feature. Normally these are produced by the Requirements Engineer and Architect agents
before the Task Planner is engaged.

**Acceptance Criteria:**
- [ ] `docs/features/124-port-to-python-or-golang/specification.md` exists and covers:
  - Functional requirements (what the ported Go tool must do)
  - Non-functional requirements (performance, security, packaging)
  - Scope (full port vs. parity-first vs. new implementation)
  - Migration strategy (replace .NET or coexist?)
  - Target platforms (Linux x64, Linux ARM64, macOS x64, macOS ARM64, Windows x64)
- [ ] `docs/features/124-port-to-python-or-golang/architecture.md` exists and covers:
  - Go module/package structure (mirroring `Parsing/`, `MarkdownGeneration/`, `CLI/`, `Providers/` layout)
  - Key Go design decisions: JSON library (`encoding/json` with struct tags), CLI library (`cobra` or `flag`), test framework (`go test` + `testify`)
  - Docker build strategy (multi-stage build, `CGO_ENABLED=0`, scratch container)
  - CI/CD pipeline changes

**Dependencies:** Task 1

---

### Task 3: New Project Scaffolding

**Priority:** High

**Description:**
Set up the new Go project structure. This includes the module layout (`go.mod`, `go.sum`),
build configuration, linter, formatter, and a minimal CLI entry point that reads a file path
from arguments and exits cleanly.

**Acceptance Criteria:**
- [ ] `src-go/` directory created with standard Go layout (`cmd/tfplan2md/`, `internal/`)
- [ ] `go.mod` initialised with the agreed module path (e.g., `github.com/51nk0r5w1m/tfplan2md`)
- [ ] `go build ./...` succeeds from a clean checkout
- [ ] `golangci-lint` configured with a `.golangci.yml` at the repo root (or `src-go/`)
- [ ] `gofmt` / `goimports` enforced via `.editorconfig` and CI
- [ ] `Dockerfile` updated (multi-stage: `golang:1.22-alpine` builder → `scratch` final image)
- [ ] CLI entry point at `cmd/tfplan2md/main.go` responds to `--help` without crashing
- [ ] GitHub Actions CI step added: `go build ./...` and `golangci-lint run`
- [ ] `CGO_ENABLED=0` set for all build and release steps to ensure static binary

**Dependencies:** Tasks 1, 2

---

### Task 4: Terraform Plan JSON Parsing

**Priority:** High

**Description:**
Implement parsing of `terraform show -json` output in Go using `encoding/json` with struct
tags. This is the foundational input stage. The existing parsing subsystem handles:
`TerraformPlan`, `ResourceChange`, `ResourceDrift`, `OutputChange`, `ConfigurationDeprecation`,
`RelevantAttribute` paths, lifecycle action triggers, and custom JSON converters.

Map each type to a corresponding Go struct in `internal/parsing/`. Use `json:` struct tags
for field mapping and implement custom `json.Unmarshaler` where needed (e.g., action arrays).

**Acceptance Criteria:**
- [ ] All existing Terraform plan JSON test fixtures parse successfully (re-use `testdata/` files)
- [ ] Handles all supported Terraform plan `format_version` values (see note below)
- [ ] Sensitive values are correctly identified from plan JSON (`sensitive: true`)
- [ ] Resource change actions (create, update, delete, replace, no-op, move, import) all parsed
- [ ] Outputs, moved blocks, and import blocks parsed
- [ ] Deprecation warnings parsed
- [ ] Unit tests cover all parsing scenarios with existing test fixtures

> **`format_version` vs `terraform_version` — important distinction:**
>
> Terraform plan JSON has two distinct version fields:
>
> | Field | Example value | What it means |
> |---|---|---|
> | `format_version` | `"1.2"` | Schema version of the plan JSON document (semver). This is what the parser must handle. |
> | `terraform_version` | `"1.15.0"` | The Terraform CLI version that produced the plan. Informational only; no parsing logic depends on it. |
>
> The Go parser must validate and handle `format_version`. As of Terraform 1.15, all plans use `format_version` `"1.2"`. The version `"1.0"` and `"1.1"` exist in older plans. The acceptance criterion is:
>
> - [ ] Parser reads and validates `format_version` from the JSON root
> - [ ] `format_version` values `"1.0"`, `"1.1"`, and `"1.2"` are all accepted
> - [ ] Unknown future `format_version` values produce a clear error (`ErrUnsupportedFormatVersion`)
> - [ ] `terraform_version` is stored as a plain string field — no parsing logic branches on it
> - [ ] The report output includes the `terraform_version` string for display only

**Dependencies:** Task 3

---

### Task 5: Core Markdown Generation Engine

**Priority:** High

**Description:**
Implement the core report model builder and Markdown writer in Go. In the existing codebase this is
`MarkdownGeneration/Rendering/` (ReportRenderer, SummaryRenderer, MarkdownWriter, HeaderRenderer)
and the report model builder that converts parsed plan data into a rendering model. Map these
to Go packages under `internal/markdown/` using `strings.Builder` or `text/template` for
Markdown generation.

**Acceptance Criteria:**
- [ ] Markdown report generated from parsed plan data matches expected output for all existing snapshot test fixtures
- [ ] Summary table (resource counts by action) rendered correctly
- [ ] Per-resource change sections rendered with before/after values
- [ ] Sensitive values masked by default
- [ ] `--show-sensitive` flag suppresses masking
- [ ] Module grouping and hierarchy preserved
- [ ] Snapshot tests for all existing `TestData/` fixtures pass

**Dependencies:** Task 4

---

### Task 6: Resource-Specific Provider Templates

**Priority:** Medium

**Description:**
Implement provider-specific rendering in Go. The existing codebase has 87 files across `Providers/AzureRM`,
`Providers/AzApi`, `Providers/AzureAD`, and `Providers/AzureDevOps`. Each provider registers
attribute filters, value formatters, and icon rules for specific resource types (e.g., firewall
rules, NSG rules, role assignments). Map to Go packages under `internal/providers/`.

Use Go interfaces to define `ProviderModule`, `AttributeFilter`, `ValueFormatter`, and
`IconProvider` — mirroring the C# interface-based design. Icon rules JSON files are embedded
using `//go:embed`.

This is the most complex and feature-rich subsystem. Port providers incrementally, starting
with the most commonly used (AzureRM core resources).

**Acceptance Criteria:**
- [ ] AzureRM provider: firewall rules, NSG rules, role assignments render with semantic diffs
- [ ] AzApi provider: resource-specific overrides applied
- [ ] AzureAD provider: resource-specific overrides applied
- [ ] AzureDevOps provider: resource-specific overrides applied
- [ ] Icon rules JSON is loaded and applied correctly
- [ ] Azure Resource ID formatting applied
- [ ] All provider-related snapshot tests pass

**Dependencies:** Task 5

---

### Task 7: CLI Interface

**Priority:** High

**Description:**
Implement the full CLI argument parser in Go matching the current interface. Use `cobra`
(recommended) or the stdlib `flag` package. All current flags and options must be supported.

Key options to support (from current codebase):
- `--input` / `-i` — input plan JSON file path
- `--output` / `-o` — output markdown file path (default: stdout)
- `--title` — custom report title
- `--show-sensitive` — show sensitive values unmasked
- `--render-target` — GitHub, AzureDevOps, Bitbucket, etc.
- `--details` — details display mode
- `--unchanged` — show unchanged values
- `--version` — print version

**Acceptance Criteria:**
- [ ] All CLI options from the current `CliParser.cs` are supported
- [ ] `--help` output is clear and documents all options
- [ ] Invalid input produces a user-friendly error message (non-zero exit code)
- [ ] `--version` prints current version
- [ ] End-to-end CLI test: given a test plan JSON, produces expected markdown output

**Dependencies:** Tasks 3, 5

---

### Task 8: Render Target Support

**Priority:** Medium

**Description:**
Implement render target adapters (GitHub, Azure DevOps, Bitbucket) in Go. The existing codebase has
`RenderTargets/` with platform-specific markdown formatting (e.g., `<details>` collapsing,
table formatting differences, icon availability). Map to Go interfaces under
`internal/rendertargets/` with a `RenderTarget` interface and concrete implementations.

**Acceptance Criteria:**
- [ ] GitHub render target produces output compatible with GitHub PR comments
- [ ] Azure DevOps render target produces output compatible with AzDo PR comments
- [ ] Bitbucket render target produces output compatible with Bitbucket PR comments
- [ ] Render target is selectable via `--render-target` CLI flag
- [ ] Default render target is GitHub (matching current behaviour)
- [ ] Snapshot tests for each render target pass

**Dependencies:** Task 5

---

### Task 9: Test Suite

**Priority:** High

**Description:**
Establish the Go test framework and port all existing snapshot-based tests. The current test
suite uses snapshot assertions and consumes fixtures from `testdata/`. In Go, use the stdlib
`testing` package with `testify/assert` for assertions and a custom snapshot helper that
reads/writes `.md` files from `testdata/`.

**Acceptance Criteria:**
- [ ] Test framework documented: stdlib `testing` + `github.com/stretchr/testify/assert`
- [ ] Snapshot test helper implemented: compares generated markdown against expected `.md` files in `testdata/`
- [ ] All existing `testdata/` fixtures have corresponding `_test.go` tests
- [ ] `go test ./...` runs all tests and fails on unexpected snapshot output changes
- [ ] `go test -coverprofile=coverage.out ./...` produces code coverage ≥ 80%
- [ ] `scripts/test-with-timeout.sh` runs `go test ./...` by default (no dotnet dependency)
- [ ] Tests run in CI on every PR

**Dependencies:** Tasks 4, 5, 6, 7, 8

---

### Task 10: Multi-Platform Binary Distribution

**Priority:** Medium

**Description:**
Implement cross-compilation and packaging for all target platforms using Go's built-in
cross-compilation support (`GOOS`/`GOARCH` environment variables, `CGO_ENABLED=0`).
The current project distributes:
- Docker image (scratch-based, ~5MB with NativeAOT)
- GitHub Releases with binaries for Linux x64, Linux ARM64, macOS, Windows x64
- Homebrew formula

**Acceptance Criteria:**
- [ ] Binaries built for: `linux/amd64`, `linux/arm64`, `darwin/amd64`, `darwin/arm64`, `windows/amd64`
- [ ] All builds use `CGO_ENABLED=0 go build -ldflags="-s -w"` for minimal static binaries
- [ ] Docker multi-stage build: `golang:1.22-alpine` builder → `scratch` final image
- [ ] Docker image size documented; must be comparable to current (~5–10MB)
- [ ] GitHub Release workflow updated to `go build` and publish new binaries
- [ ] Homebrew formula updated for new Go binary download URLs
- [ ] All release artifacts verified to run on target platforms

**Dependencies:** Task 3, Task 7

---

### Task 11: CI/CD Pipeline Updates

**Priority:** Medium

**Description:**
Update all GitHub Actions workflows to build, test, and release the new Go project.
The existing .NET build steps must not be removed — they remain in place for the .NET codebase.
Add parallel Go build/test/release steps alongside the existing .NET steps.

**Acceptance Criteria:**
- [ ] CI workflow has a `go-build` job: `go build ./...` + `golangci-lint run`
- [ ] CI workflow has a `go-test` job: `go test -race -coverprofile=coverage.out ./...` (see CGO note below)
- [ ] Release workflow has a `go-release` job: cross-compiles all target platforms and uploads binaries
- [ ] Code coverage report for Go published in CI (e.g., using `codecov` or `coveralls`)
- [ ] Static analysis via `golangci-lint` integrated in CI (fail on lint errors)

> **CGO_ENABLED=0 vs `go test -race` — architecture impact:**
>
> Go's race detector is implemented using CGO (it instruments the binary with a C runtime). This
> creates a conflict when `CGO_ENABLED=0` is set globally:
>
> | Job type | `CGO_ENABLED` | `-race` | Why |
> |---|---|---|---|
> | `go-build` (PR validation) | `0` | No | Static binary verification; CGO disabled for reproducibility |
> | `go-test` (PR validation) | *not set* (default `1`) | Yes | Race detector requires CGO; runs on standard hosted runner |
> | `go-release` (cross-compile) | `0` | No | Must produce static binaries for scratch Docker and all target platforms |
>
> **Implementation rule:** `CGO_ENABLED=0` is set **only** in build and release steps that produce
> distribution artifacts. Test jobs use the default CGO setting (`CGO_ENABLED=1`) so that `-race`
> works correctly. On Windows the race detector is supported; on `linux/arm64` GitHub-hosted
> runners it is also available since Go 1.21. The `go-release` job never uses `-race`.
>
> **Implication for scratch Docker images:** The final Docker image is built from a `CGO_ENABLED=0`
> static binary so it runs on `scratch` without glibc. The test image (used only in CI) may use a
> glibc-based runner.

**Dependencies:** Tasks 3, 9, 10

---

### Task 12: Documentation Updates

**Priority:** Low

**Description:**
Update all user-facing documentation to reference Go alongside (or instead of) .NET where
applicable. Do not remove any existing documentation — refactor to reference Go.

**Acceptance Criteria:**
- [ ] `README.md` updated: Go badge replaces the .NET badge; installation instructions include `go install` option; development setup references Go toolchain
- [ ] `CONTRIBUTING.md` development setup references Go toolchain requirements (Go 1.22+, `golangci-lint`)
- [ ] `docs/architecture.md` updated with a Go architecture section
- [ ] `docs/spec.md` updated to reference Go as the implementation language
- [ ] `docs/features.md` updated if any user-facing behaviour changes
- [ ] Docker usage examples updated to reflect the Go-based image
- [ ] All `.NET`, `C#`, or `dotnet` references in documentation ported to Go equivalents

**Dependencies:** Tasks 3–11

---

## Implementation Order

Recommended sequence for implementation:

1. **Task 1** — Golang ADR (documents confirmed decision; unblocks all other work)
2. **Task 2** — Formal specification and architecture document (unblocks Tasks 3–12)
3. **Task 3** — Go project scaffolding (enables parallel work on Tasks 4 and 7)
4. **Task 4** — JSON parsing in Go (foundation for markdown generation)
5. **Task 7** — CLI interface in Go (can be developed in parallel with Task 4)
6. **Task 5** — Core markdown generation in Go (depends on Task 4)
7. **Task 9** — Go test suite (can be started alongside Task 5)
8. **Task 8** — Render target support in Go (refines Task 5 output)
9. **Task 6** — Provider templates in Go (most complex; built on top of Tasks 5 and 8)
10. **Task 10** — Multi-platform Go binary distribution (built on Tasks 3 and 7)
11. **Task 11** — CI/CD pipeline updates for Go (finalised after tests pass)
12. **Task 12** — Documentation updates to reference Go (last, after all functionality complete)

---

## Open Questions

> Language choice is **resolved** (Golang — confirmed by Maintainer). Remaining questions:

1. **Scope: full port vs. functional parity first?**
   - Should the Go port implement 100% of existing provider templates and resource-specific
     logic in the initial release, or target core functionality first with providers added
     incrementally in follow-up features?

2. **Migration strategy: full replace or coexist?**
   - Should the Go implementation replace the existing project entirely, or should
     both be maintained in parallel? The current tasks assume coexistence (no existing files removed).

3. **Version continuity**: Should semantic versioning continue from the current .NET version,
   or should the Go port start at `1.0.0` as a clean slate?

4. **CLI library choice**: `cobra` (feature-rich, widely used in Go CLIs) vs. stdlib `flag`
   (simpler, no dependencies). Recommend `cobra` given the number of flags and subcommands.

5. **Test fixture reuse**: The existing `TestData/` fixtures (Terraform plan JSON + expected
   markdown snapshots) should be reused as-is by the Go tests. Confirm no path or format
   incompatibilities exist.
