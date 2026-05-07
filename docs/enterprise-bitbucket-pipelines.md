# Enterprise and Bitbucket Pipelines guide

This guide describes production-oriented usage patterns for `tfplan2md` in enterprise CI/CD environments, with Bitbucket Pipelines as the primary example.

## Goals

- Generate pull-request-safe Terraform plan reports for Bitbucket Cloud.
- Keep large reports available as pipeline artifacts when PR comments become too large.
- Use pinned and auditable installation sources in regulated environments.
- Preserve traceability for audit, security review, and change approval workflows.

## Bitbucket Pipelines pull request workflow

Use the Bitbucket render target when posting reports to Bitbucket PR comments:

```yaml
image: hashicorp/terraform:1.14

pipelines:
  pull-requests:
    "**":
      - step:
          name: Terraform plan report
          oidc: true
          services:
            - docker
          script:
            - terraform init -input=false
            - terraform plan -input=false -out=plan.tfplan
            - terraform show -json plan.tfplan > plan.json
            - export TFPLAN2MD_VERSION=1.0.0 # Replace with the approved release version for your organization.
            - docker run --rm -v "$PWD:/workspace" -w /workspace "oocx/tfplan2md:${TFPLAN2MD_VERSION}" plan.json --render-target bitbucket --details closed --output tfplan2md-report.md
            - scripts/bitbucket-pr-comment.py --report tfplan2md-report.md --artifact-url "https://bitbucket.org/${BITBUCKET_WORKSPACE}/${BITBUCKET_REPO_SLUG}/pipelines/results/${BITBUCKET_BUILD_NUMBER}"
          artifacts:
            - tfplan2md-report.md
```

The helper script updates a single bot-owned PR comment by using a hidden marker. If the report exceeds the configured comment limit, the PR comment is replaced with a short fallback message that includes an HTML artifact link:

```html
<a href="https://bitbucket.org/example/workload/pipelines/results/123">tfplan2md report artifact</a>
```

The helper uses the short-lived `BITBUCKET_STEP_OIDC_TOKEN` emitted by Bitbucket Pipelines when `oidc: true` is enabled on the step. Do not hardcode app passwords or long-lived API tokens in pipeline YAML. The script also reads `BITBUCKET_WORKSPACE`, `BITBUCKET_REPO_SLUG`, and `BITBUCKET_PR_ID` from the pull request pipeline environment.

> Bitbucket OIDC is designed for short-lived trust with OIDC-aware services. If your Bitbucket Cloud REST API tenant cannot accept `BITBUCKET_STEP_OIDC_TOKEN` directly for PR comments, route comment creation through an internal OIDC-aware broker or API gateway and set `BITBUCKET_API_BASE_URL` to that broker's Bitbucket-compatible endpoint. This keeps the pipeline free of hardcoded credentials while preserving the same helper script.

## Binary-based Bitbucket Pipelines usage

Use pre-built binaries when Docker is unavailable or restricted:

```yaml
pipelines:
  pull-requests:
    "**":
      - step:
          name: Terraform plan report
          oidc: true
          image: hashicorp/terraform:1.14
          script:
            - apk add --no-cache curl python3
            - export TFPLAN2MD_VERSION=1.0.0
            - curl -fsSLO "https://github.com/oocx/tfplan2md/releases/download/v${TFPLAN2MD_VERSION}/tfplan2md_${TFPLAN2MD_VERSION}_linux-musl-x64.tar.gz"
            - curl -fsSLO "https://github.com/oocx/tfplan2md/releases/download/v${TFPLAN2MD_VERSION}/SHA256SUMS"
            - sha256sum -c SHA256SUMS --ignore-missing
            - tar -xzf "tfplan2md_${TFPLAN2MD_VERSION}_linux-musl-x64.tar.gz"
            - terraform init -input=false
            - terraform plan -input=false -out=plan.tfplan
            - terraform show -json plan.tfplan > plan.json
            - ./tfplan2md plan.json --render-target bitbucket --output tfplan2md-report.md
            - scripts/bitbucket-pr-comment.py --report tfplan2md-report.md --artifact-url "https://bitbucket.org/${BITBUCKET_WORKSPACE}/${BITBUCKET_REPO_SLUG}/pipelines/results/${BITBUCKET_BUILD_NUMBER}"
          artifacts:
            - tfplan2md-report.md
```

## Large report strategy

Bitbucket comments should stay concise. For large plans:

- Use `--details closed` to keep comments scannable.
- Use `--template summary` when reviewers only need high-level changes in the PR.
- Always publish `tfplan2md-report.md` as a pipeline artifact.
- Pass `--artifact-url` or `TFPLAN2MD_ARTIFACT_URL` to `scripts/bitbucket-pr-comment.py`.
- Lower `--max-comment-chars` if your organization wants shorter PR comments.

Example:

```bash
scripts/bitbucket-pr-comment.py \
  --report tfplan2md-report.md \
  --max-comment-chars 20000 \
  --artifact-url "https://bitbucket.org/${BITBUCKET_WORKSPACE}/${BITBUCKET_REPO_SLUG}/pipelines/results/${BITBUCKET_BUILD_NUMBER}"
```

## Monorepos and multiple workspaces

For repositories with multiple Terraform roots, generate one report per root and keep artifact names stable:

```bash
for root in infra/network infra/platform infra/apps; do
  (
    cd "$root"
    terraform init -input=false
    terraform plan -input=false -out=plan.tfplan
    terraform show -json plan.tfplan > plan.json
    tfplan2md plan.json \
      --render-target bitbucket \
      --details closed \
      --report-title "Terraform Plan Report - ${root}" \
      --output "../../artifacts/tfplan2md-${root//\//-}.md"
  )
done
```

Publish the `artifacts/*.md` files from the pipeline, and post either a summary report or one PR comment per Terraform root.

## Security and governance guidance

- Keep sensitive values masked. Do not use `--show-sensitive` in shared CI unless a documented exception exists.
- Treat generated reports as infrastructure metadata. Configure artifact retention according to your data classification policy.
- Use pinned Docker tags or checksum-verified binaries instead of floating `latest` tags.
- Mirror release artifacts or Docker images into internal registries for air-gapped environments.
- Use Bitbucket Pipelines OIDC (`oidc: true`) for artifact uploads and PR comment integration through OIDC-aware services.
- Do not hardcode Bitbucket app passwords or long-lived API tokens in pipeline YAML.
- Use SARIF inputs from tools such as Checkov, Trivy, TFLint, or Semgrep, and fail the pipeline when findings exceed the approved severity threshold.

Example security gate:

```bash
tfplan2md plan.json \
  --render-target bitbucket \
  --code-analysis-results "reports/*.sarif" \
  --code-analysis-minimum-level medium \
  --fail-on-static-code-analysis-errors high \
  --output tfplan2md-report.md
```

## Enterprise deployment patterns

Recommended production patterns:

- Pin Docker images by version, and by digest where your registry policy requires it.
- Verify binary checksums before execution.
- Mirror Docker images and release archives into approved internal artifact stores.
- Keep previous approved versions available for rollback.
- Include the generated report as an immutable build artifact for audit trails.
- Name artifacts with environment, Terraform workspace, pull request ID, and commit SHA when possible.

## Custom policy rules

Use `scripts/tfplan2md-policy.py` to enforce enterprise rules before posting the report. The policy helper is written in Python and supports rules such as "Terraform changes can be made by Alice, but only when the target branch is `develop`."

Example policy file:

```json
{
  "rules": [
    {
      "name": "terraform changes only by alice on develop",
      "when": {
        "hasChanges": true
      },
      "allow": {
        "actors": ["alice"],
        "targetBranches": ["develop"]
      },
      "message": "Terraform changes require Alice as the actor and develop as the target branch."
    }
  ]
}
```

Pipeline usage:

```bash
scripts/tfplan2md-policy.py \
  --policy tfplan2md-policy.json \
  --plan-json plan.json \
  --actor "$BITBUCKET_STEP_TRIGGERER_UUID" \
  --target-branch "$BITBUCKET_PR_DESTINATION_BRANCH"
```

The helper exits with code `20` when a policy denies the change, allowing the pipeline to fail before a report is posted.

Example artifact naming convention:

```text
tfplan2md-${BITBUCKET_DEPLOYMENT_ENVIRONMENT}-${TF_WORKSPACE}-pr-${BITBUCKET_PR_ID}-${BITBUCKET_COMMIT}.md
```

## Acceptance checklist

- [ ] Pull request pipelines generate `plan.json` from `terraform show -json`.
- [ ] `tfplan2md` runs with `--render-target bitbucket`.
- [ ] Full reports are published as Bitbucket Pipeline artifacts.
- [ ] Oversized PR comments include an HTML link to the artifact.
- [ ] OIDC is enabled on Bitbucket Pipeline steps that publish artifacts or comments.
- [ ] No hardcoded credentials are stored in pipeline YAML.
- [ ] Custom policy rules are evaluated before comments are posted.
- [ ] Docker images or binaries are pinned and verified.
- [ ] Security findings are included and gated according to policy.
