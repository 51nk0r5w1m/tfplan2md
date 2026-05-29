---
name: run-dotnet-tests
description: Run Go tests correctly using the test-with-timeout.sh wrapper to prevent test hangs.
---

# Run Go Tests

## Purpose
Provide standardized instructions for running Go tests correctly. Ensures agents use the
`scripts/test-with-timeout.sh` wrapper instead of calling `go test` directly in contexts where
hung tests would block CI or the agent session.

## When to Use This Skill
- Before committing code changes that affect Go code in `src-go/`
- When verifying bug fixes or new features
- When running targeted tests during development
- When the full test suite must pass before marking work complete

## Hard Rules

### Must
- **ALWAYS** use `scripts/test-with-timeout.sh` wrapper for long-running or CI test runs
- Run tests from `src-go/` (the wrapper handles directory changes automatically)
- Use `./...` to run all tests in the module
- Use `-race` in CI to detect data races
- Wait for test completion and check exit code (0 = pass, non-zero = fail)

### Must Not
- **NEVER** ignore test failures or skip tests to make CI pass
- Never manually edit golden/snapshot files in `src-go/testdata/snapshots/` — use the `update-test-snapshots` skill
- Never modify test expectations to match broken output — fix the code, not the tests

## Common Test Commands

### Run Full Test Suite
```bash
scripts/test-with-timeout.sh
```

### Run with Race Detector (CI standard)
```bash
scripts/test-with-timeout.sh -- go test -race ./...
```

### Run with Coverage
```bash
scripts/test-with-timeout.sh -- go test -race -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
```

### Run a Specific Package
```bash
scripts/test-with-timeout.sh -- go test -v ./internal/parsing/...
```

### Run a Specific Test by Name
```bash
scripts/test-with-timeout.sh -- go test -run TestParsePlan_ValidJSON ./internal/parsing/...
```

### Run Table-Driven Subtest
```bash
scripts/test-with-timeout.sh -- go test -run TestRender/create_resource ./internal/markdown/...
```

### Run Integration Tests (tagged)
```bash
scripts/test-with-timeout.sh --timeout-seconds 300 -- go test -race -tags=integration ./test/...
```

### Run Fuzz Tests
```bash
# Fuzz for 60 seconds (do not use wrapper — fuzz runs indefinitely by design)
cd src-go && go test ./internal/parsing/... -fuzz=FuzzParsePlan -fuzztime=60s
```

### Run with Longer Timeout
```bash
scripts/test-with-timeout.sh --timeout-seconds 300
```

## Interpreting Test Output

### Pass
```
ok  github.com/51nk0r5w1m/tfplan2md/internal/parsing0.234s
ok  github.com/51nk0r5w1m/tfplan2md/internal/markdown1.456s
```

### Fail
```
--- FAIL: TestRender_ValidPlan (0.003s)
    renderer_test.go:45: expected "# Terraform Plan" but got "# Plan"
FAIL
FAILgithub.com/51nk0r5w1m/tfplan2md/internal/markdown0.005s
```

### Race Detected
```
WARNING: DATA RACE
Write at 0x... by goroutine 7:
...
```

## Snapshot / Golden File Updates

When snapshot output changes intentionally, regenerate them using `scripts/update-test-snapshots.sh`
or by running tests with the `UPDATE_SNAPSHOTS=1` environment variable:

```bash
UPDATE_SNAPSHOTS=1 go test ./internal/markdown/...
```

See the `update-test-snapshots` skill for full instructions.

## Coverage Requirements

CI enforces a minimum coverage threshold (≥ 80%). Check coverage locally:

```bash
go test -race -coverprofile=coverage.out ./...
go tool cover -func=coverage.out | grep "total:"
```

## Golangci-lint

Always run the linter alongside tests:

```bash
golangci-lint run ./...
```

CI runs `golangci-lint` in a separate `go-lint` job and fails on any lint error.
