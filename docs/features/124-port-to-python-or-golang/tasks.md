# Tasks: Port tfplan2md to Python or Golang

## Overview

Port the existing .NET 10 / C# 13 `tfplan2md` CLI tool to either Python or Golang.
The tool converts Terraform plan JSON files into human-readable Markdown reports.

Reference: [Problem statement](../../../.github/) — "This needs to be ported to either python or golang"

> ⚠️ **Prerequisites Missing**: This feature was submitted directly to the Task Planner without
> passing through the Requirements Engineer or Architect phases. A formal specification and
> architecture document have not been created. The open questions section at the bottom of this
> document captures decisions that must be resolved before implementation can begin.
>
> **The most critical blocker is Task 1 (language selection)**. No other task can start until
> that decision is made.

---

## Tasks

### Task 1: Language Selection and Architecture Decision Record

**Priority:** High (Blocker — must be completed before all other tasks)

**Description:**
Decide between Python and Golang as the target language and document the rationale in an ADR.
This decision has significant downstream implications for distribution, performance, Docker image
size, and maintainability.

Key trade-offs to evaluate:

| Criterion | Python | Golang |
|-----------|--------|--------|
| Binary size / distribution | Requires runtime or PyInstaller | Single static binary (similar to current NativeAOT) |
| Docker image | Larger image needed | Scratch container possible (like current) |
| Dev speed | Faster iteration | More verbose but stricter typing |
| CI/CD pipeline integration | pip install or bundled binary | `go install` or pre-built binary |
| Community familiarity | Widely known | Growing DevOps adoption |
| Closest to existing architecture | Less similar | Closer to C# idioms |

**Acceptance Criteria:**
- [ ] Language choice is documented in `docs/adr-NNN-port-language-selection.md`
- [ ] ADR covers: context, decision, rationale, trade-offs, and consequences
- [ ] Maintainer has explicitly approved the decision

**Dependencies:** None

**Notes:**
This decision is required before any other task is started. The architecture team (or
Maintainer) should drive this decision with input from the current codebase analysis.

---

### Task 2: Formal Specification and Architecture Document

**Priority:** High (Blocker — must be completed before Tasks 3–11)

**Description:**
Create the missing specification (`specification.md`) and architecture (`architecture.md`) for
this feature. Normally these are produced by the Requirements Engineer and Architect agents
before the Task Planner is engaged.

**Acceptance Criteria:**
- [ ] `docs/features/124-port-to-python-or-golang/specification.md` exists and covers:
  - Functional requirements (what the ported tool must do)
  - Non-functional requirements (performance, security, packaging)
  - Scope (full port vs. parity-first vs. new implementation)
  - Migration strategy (replace .NET or coexist?)
  - Target platforms (Linux x64, Linux ARM64, macOS, Windows)
- [ ] `docs/features/124-port-to-python-or-golang/architecture.md` exists and covers:
  - Module/package structure in the target language
  - Key design decisions (JSON parsing library, CLI library, test framework)
  - Docker build strategy
  - CI/CD pipeline changes

**Dependencies:** Task 1

---

### Task 3: New Project Scaffolding

**Priority:** High

**Description:**
Set up the new project structure in the chosen language. This includes the module layout,
build system, linter, formatter, and a minimal "hello world" CLI that reads a file path from
arguments and exits cleanly.

**Acceptance Criteria:**
- [ ] New project root exists (e.g., `src-go/` or `src-py/`) with standard layout for the language
- [ ] Build succeeds from a clean checkout (`go build ./...` or `pip install -e .` / `uv sync`)
- [ ] Linter and formatter are configured (e.g., `golangci-lint`, `ruff`/`mypy`)
- [ ] `.editorconfig` / lint config added for the new language
- [ ] `Dockerfile` updated (or a new one added) to build and package the new binary
- [ ] CLI entry point exists and accepts `--help` without crashing
- [ ] CI workflow step added to build the new project

**Dependencies:** Tasks 1, 2

---

### Task 4: Terraform Plan JSON Parsing

**Priority:** High

**Description:**
Implement parsing of `terraform show -json` output. This is the foundational input stage.
The existing C# `Parsing/` subsystem handles: `TerraformPlan`, `ResourceChange`,
`ResourceDrift`, `OutputChange`, `ConfigurationDeprecation`, `RelevantAttribute` paths,
lifecycle action triggers, and custom JSON converters.

**Acceptance Criteria:**
- [ ] All existing Terraform plan JSON test fixtures parse successfully (re-use `TestData/` files)
- [ ] Handles terraform format versions currently supported (1.x through 1.15+)
- [ ] Sensitive values are correctly identified from plan JSON (`sensitive: true`)
- [ ] Resource change actions (create, update, delete, replace, no-op, move, import) all parsed
- [ ] Outputs, moved blocks, and import blocks parsed
- [ ] Deprecation warnings parsed
- [ ] Unit tests cover all parsing scenarios with existing test fixtures

**Dependencies:** Task 3

---

### Task 5: Core Markdown Generation Engine

**Priority:** High

**Description:**
Implement the core report model builder and Markdown writer. In the C# codebase this is
`MarkdownGeneration/Rendering/` (ReportRenderer, SummaryRenderer, MarkdownWriter, HeaderRenderer)
and the report model builder that converts parsed plan data into a rendering model.

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
Implement provider-specific rendering. The C# codebase has 87 files across `Providers/AzureRM`,
`Providers/AzApi`, `Providers/AzureAD`, and `Providers/AzureDevOps`. Each provider registers
attribute filters, value formatters, and icon rules for specific resource types (e.g., firewall
rules, NSG rules, role assignments).

This is the most complex and feature-rich subsystem. It is recommended to port providers
incrementally, starting with the most commonly used (AzureRM core resources).

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
Implement the full CLI argument parser matching the current interface defined in
`CLI/CliParser.cs`. All current flags and options must be supported.

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
Implement render target adapters (GitHub, Azure DevOps, Bitbucket). The C# codebase has
`RenderTargets/` with platform-specific markdown formatting (e.g., `<details>` collapsing,
table formatting differences, icon availability).

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
Establish the test framework and port all existing snapshot-based tests. The current test
suite has 192 test files and uses TUnit with snapshot assertions. Tests consume fixtures from
`TestData/`.

**Acceptance Criteria:**
- [ ] Test framework chosen and documented (e.g., pytest for Python; testing + testify for Go)
- [ ] Snapshot test mechanism implemented (compare generated markdown against expected files)
- [ ] All existing `TestData/` fixtures have corresponding tests
- [ ] Tests run in CI and fail on unexpected output changes
- [ ] Code coverage ≥ 80% (matching current project target)
- [ ] `scripts/test-with-timeout.sh` updated or replaced to run new test suite

**Dependencies:** Tasks 4, 5, 6, 7, 8

---

### Task 10: Multi-Platform Binary Distribution

**Priority:** Medium

**Description:**
Implement cross-compilation and packaging for all target platforms. The current project
distributes:
- Docker image (scratch-based, ~5MB with NativeAOT)
- GitHub Releases with binaries for Linux x64, Linux ARM64, macOS, Windows x64
- Homebrew formula

**Acceptance Criteria:**
- [ ] Binaries built for: linux/amd64, linux/arm64, darwin/amd64, darwin/arm64, windows/amd64
- [ ] Docker image updated to use new binary (scratch container if Go; slim container if Python)
- [ ] Docker image size is documented; must be ≤ current size or justified if larger
- [ ] GitHub Release workflow updated to publish new binaries
- [ ] Homebrew formula updated for new binary
- [ ] All release artifacts verified to run on target platforms

**Dependencies:** Task 3, Task 7

---

### Task 11: CI/CD Pipeline Updates

**Priority:** Medium

**Description:**
Update all GitHub Actions workflows to build, test, and release the new language project.
Remove or archive .NET-specific build steps if the .NET project is being replaced.

**Acceptance Criteria:**
- [ ] CI runs new build and test on every PR
- [ ] Release workflow publishes new binaries to GitHub Releases
- [ ] Code coverage report updated in CI
- [ ] Static analysis / linter integrated in CI
- [ ] .NET build steps removed or clearly marked as deprecated (if full replacement)

**Dependencies:** Tasks 3, 9, 10

---

### Task 12: Documentation Updates

**Priority:** Low

**Description:**
Update all user-facing documentation to reflect the new language and distribution mechanism.

**Acceptance Criteria:**
- [ ] `README.md` installation instructions updated for new binary/package
- [ ] `CONTRIBUTING.md` development setup updated (e.g., Go toolchain, Python venv)
- [ ] `docs/architecture.md` updated to reflect new architecture
- [ ] `docs/features.md` updated if any user-facing behaviour changed
- [ ] `docs/spec.md` updated to reflect the new technology stack
- [ ] Docker usage examples updated

**Dependencies:** Tasks 3–11

---

## Implementation Order

Recommended sequence for implementation:

1. **Task 1** — Language selection ADR (blocker for all other work)
2. **Task 2** — Formal specification and architecture document (blocker for Tasks 3–12)
3. **Task 3** — Project scaffolding (enables parallel work on Tasks 4 and 7)
4. **Task 4** — JSON parsing (foundation for markdown generation)
5. **Task 7** — CLI interface (can be developed in parallel with Task 4)
6. **Task 5** — Core markdown generation (depends on Task 4)
7. **Task 9** — Test suite setup (can be started alongside Task 5)
8. **Task 8** — Render target support (refines Task 5 output)
9. **Task 6** — Provider templates (most complex; built on top of Tasks 5 and 8)
10. **Task 10** — Distribution packaging (built on Task 3 scaffolding and Task 7 CLI)
11. **Task 11** — CI/CD pipeline updates (finalised after Tests pass)
12. **Task 12** — Documentation updates (last, after all functionality is complete)

---

## Open Questions

> These must be resolved before implementation can begin.

1. **Language choice**: Python or Golang? See Task 1 for trade-off analysis.
   - Recommendation: **Golang** — produces a self-contained static binary compatible with scratch
     Docker containers, closely matching the current NativeAOT distribution model, and aligns well
     with the DevOps tooling ecosystem where this tool is used.

2. **Scope: full port vs. functional parity?**
   - Should the port implement 100% of existing provider templates and resource-specific logic,
     or should it target core functionality first with providers added incrementally?

3. **Migration strategy: replace .NET or coexist?**
   - Should the new language implementation replace the .NET project entirely, or should both
     be maintained during a transition period?

4. **Version continuity**: Should semantic versioning continue from the current version, or
   should the port start at `1.0.0` as a clean slate?

5. **Test fixture reuse**: The existing `TestData/` fixtures (Terraform plan JSON + expected
   markdown snapshots) should be reused as-is. Is there any concern about compatibility?
