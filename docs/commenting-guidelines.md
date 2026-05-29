# Code Commenting Guidelines

This document defines the standards for code comments in the tfplan2md project. Well-written comments make code more maintainable and help both human developers and AI agents understand and reason about the codebase.

## Core Principles

1. **Comments should explain "why", not "what"**
   - The code itself shows *what* it does
   - Comments should explain *why* a particular approach was chosen
   - Provide context that cannot be inferred from reading the code alone

2. **All exported identifiers must be documented**
   - All exported types, functions, methods, constants, and variables require Go doc comments
   - Unexported identifiers should have comments when the purpose is not immediately obvious
   - Even unexported implementation details benefit from "why" comments

3. **Comments must add value**
   - Don't repeat what's already obvious from the code
   - Provide additional context, reasoning, or constraints
   - Link to relevant specifications, ADRs, or features when applicable

4. **Keep comments synchronized with code**
   - Update comments whenever code changes
   - Outdated comments are worse than no comments

## Go Doc Comments

### Format Requirements

Go doc comments are plain text comments that immediately precede the documented declaration with no blank line. They always begin with `//` for single declarations. The first sentence should start with the name of the declared identifier.

See [Go doc comment specification](https://go.dev/doc/comment) for the full reference.

#### Packages

```go
// Package parsing implements parsing of Terraform plan JSON files.
//
// It converts the JSON output of `terraform show -json` into strongly-typed
// Go structs. This package follows the Terraform JSON plan format specification
// v1.x and handles format versions 1.0 through 1.15+.
//
// The primary entry point is ParsePlan, which accepts a file path and returns
// a *Plan containing all resource changes, outputs, and deprecation warnings.
package parsing
```

#### Types

```go
// Plan represents a parsed Terraform plan JSON file.
//
// It is the root type returned by ParsePlan and contains all resource changes,
// output changes, and deprecation warnings found in the plan.
// Sensitive values are identified but not automatically redacted at this layer;
// redaction is handled by the markdown rendering layer based on the --show-sensitive flag.
type Plan struct {
    // FormatVersion is the Terraform plan format version (e.g., "1.2").
    FormatVersion string
    // ResourceChanges contains all resource changes in the plan.
    ResourceChanges []ResourceChange
}
```

**Required for all exported types:**
- First sentence: brief description starting with the type name
- Additional paragraph (optional): design decisions, usage notes, constraints

**Optional:**
- `// Deprecated: Use NewType instead.` prefix for deprecated types

#### Functions and Methods

```go
// ParsePlan reads the Terraform plan JSON file at path and returns the parsed plan.
//
// It uses streaming JSON decoding to handle large plan files efficiently;
// memory usage stays constant regardless of file size.
//
// ParsePlan returns an error if the file cannot be read, if the JSON is malformed,
// or if the format version is not supported.
//
// Related feature: docs/features/008-comprehensive-demo/
func ParsePlan(path string) (*Plan, error) {
    // implementation
}
```

**Required for all exported functions:**
- First sentence starting with the function name
- Error conditions documented in the comment body

**Optional:**
- Usage example via a separate `Example*` function in `_test.go`
- Links to related features or specs

#### Methods on Types

```go
// String returns the action as a human-readable string (e.g., "create", "update", "delete").
func (a Action) String() string {
    // implementation
}
```

#### Constants and Variables

```go
// DefaultTitle is the report title used when no --title flag is provided.
const DefaultTitle = "Terraform Plan"

// ErrUnsupportedFormatVersion is returned when the plan JSON uses a format
// version not supported by this version of tfplan2md.
var ErrUnsupportedFormatVersion = errors.New("unsupported plan format version")
```

### Advanced Comment Patterns

#### Deprecated Identifiers

Use `// Deprecated:` as the first line of the doc comment:

```go
// Deprecated: Use ParsePlan instead. ParsePlanLegacy will be removed in v2.0.
func ParsePlanLegacy(path string) (*Plan, error) {
    return ParsePlan(path)
}
```

#### Cross-References

Use `[TypeName]` or `[pkg.TypeName]` syntax for cross-references (Go 1.19+):

```go
// ResourceChange describes a single resource change in a Terraform plan.
//
// See [Plan] for the root type that contains a slice of ResourceChange.
// See [Action] for the set of valid change actions.
type ResourceChange struct {
    // ...
}
```

#### Examples in Doc Comments

For complex types, use a separate `Example*` function in `_test.go`:

```go
// In parsing_test.go:
func ExampleParsePlan() {
    plan, err := parsing.ParsePlan("testdata/create-only-plan.json")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(len(plan.ResourceChanges))
    // Output: 3
}
```

## Implementation Comments (Non-Doc)

For inline comments within function bodies, use `//` single-line comments:

### When to Use Implementation Comments

1. **Explaining non-obvious algorithms**
   ```go
   // Use binary search since roleDefinitions is sorted by ID (O(log n)).
   idx := sort.Search(len(roleDefinitions), func(i int) bool {
       return roleDefinitions[i].ID >= targetID
   })
   ```

2. **Documenting workarounds or constraints**
   ```go
   // WORKAROUND: encoding/json does not support custom unmarshalers on
   // embedded struct fields. Unmarshal manually and assign.
   // See: https://github.com/golang/go/issues/6213
   var raw rawPlan
   if err := json.Unmarshal(data, &raw); err != nil {
       return err
   }
   ```

3. **Explaining business logic or domain rules**
   ```go
   // Azure RBAC assignments at management group scope use a different
   // ID format ("/providers/Microsoft.Management/...") and are handled separately.
   if strings.HasPrefix(scope, "/subscriptions/") {
       // process subscription-scoped assignment
   }
   ```

4. **Marking future improvements**
   ```go
   // TODO: Cache role definitions to reduce repeated lookups.
   // Related to feature: role-assignment-readable-display
   role, err := fetchRoleDefinition(ctx, roleID)
   ```

### When NOT to Use Implementation Comments

Avoid comments that simply restate the code:

❌ **Bad:**
```go
// increment counter by 1
counter++

// check if user is admin
if user.Role == "admin" {
    // do nothing
}
```

✅ **Good** (only comment if there's a reason):
```go
counter++

// Skip admin users — they have global permissions and ignore role-based filters.
if user.Role != "admin" {
    applyRolePermissions(user)
}
```

## Traceability to Features

When a type or function implements a specific feature, reference it in comments:

```go
// ResourceTypeSummaryGenerator generates a summary table showing resource counts by type.
//
// Implements feature: Summary Resource Type Breakdown
// Specification: docs/features/005-summary-resource-type-breakdown/specification.md
type ResourceTypeSummaryGenerator struct {
    // implementation
}
```

This helps trace code back to requirements and makes impact analysis easier during changes.

## Linter Suppressions

Use `//nolint` sparingly to suppress false-positive linter warnings. Always include a justification.

### Required Suppression Practices

1. **Use `//nolint:lintername`** on the narrowest possible scope (line or function).
2. **Include a justification** immediately after the directive.
3. **Document the why** with a comment above the suppressed code.
4. **Maintainer approval is required** for new suppressions.

Example:
```go
// Complex state machine for RFC 9110 HTTP semantics requires > 15 branches.
// Approved by maintainer in PR #346.
//nolint:cyclop // RFC 9110 requires explicit handling of each status class
func processRequest(req *http.Request) httpStatus {
    // implementation
}
```

### Line Length Exceptions

Line length suppressions are acceptable only for content that cannot be reasonably wrapped:

- Long URLs that must remain intact
- Error messages or user-facing text where wrapping changes meaning
- Embedded JSON/YAML strings where formatting is required by the consumer

## Comment Maintenance

### During Code Reviews

Code reviewers must verify:
- All exported identifiers have Go doc comments starting with the identifier name
- Comments explain "why" not just "what"
- Feature references are included where applicable
- No outdated comments remain

### During Refactoring

When modifying code:
1. Update all affected doc comments
2. Review inline comments for accuracy
3. Add new comments for new logic
4. Remove comments that no longer apply

## Tools and Validation

### Enabling Doc Comment Linting

`golangci-lint` with the `revive` and `godot` linters enforces comment formatting:

```yaml
# .golangci.yml
linters:
  enable:
    - godot    # checks that doc comments end with a period
    - godox    # checks for TODO/FIXME/HACK comments
    - revive   # reports missing doc comments on exported identifiers
```

### IDE Support

VS Code with the Go extension (gopls) provides:
- IntelliSense showing Go doc comments on hover
- Quick Info tooltips
- Automatic doc comment stub generation when typing `//` above a declaration

## References

- [Go Doc Comments](https://go.dev/doc/comment)
- [Effective Go — Commentary](https://go.dev/doc/effective_go#commentary)
- [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments)
- [golangci-lint](https://golangci-lint.run/)

## Summary

Good comments serve as documentation for both current and future maintainers (human and AI). They should:

- ✅ Explain *why* decisions were made
- ✅ Document all exported identifiers (starting with the identifier name)
- ✅ Provide context not visible in the code
- ✅ Reference specifications and features for traceability
- ✅ Stay synchronized with code changes
- ❌ Not simply repeat what the code already shows
