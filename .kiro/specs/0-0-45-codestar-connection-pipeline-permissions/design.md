# Design: CodeStar/CodeConnections Pipeline Management Permissions

**Spec:** `0-0-45-codestar-connection-pipeline-permissions`
**Repository version:** v0.0.45 (unreleased)
**Status:** Draft for review

## Overview

Grant the prefix-based Pipeline Management deployer role an opt-in, least-privilege permission to pass and use the account-wide GitHub CodeConnections connection, resolving the `codestar-connections:PassConnection` AccessDenied that blocks deployment of `template-pipeline-github.yml`. The grant is gated by a new `EnableGitHubConnectionAccess` toggle on `prefix-based-infrastructure.yml`, scoped to the single connection ARN imported from the account-wide export, and guarded by a `PassedToService` condition. All changes are additive and backward compatible. Decisions are locked in `PLAN.md` §5.

## Architecture

```
account-wide-infrastructure.yml
  └── AWS::CodeConnections::Connection  "${OrgPrefix}-${GitHubOrg}-github-connection"
        └── Export: ${OrgPrefix}-GitHub-Connection-Arn        ← source of truth for the ARN

prefix-based-infrastructure.yml  (admin, per prefix)
  ├── NEW Parameter:  EnableGitHubConnectionAccess ("true"|"false", default "false")
  ├── NEW Condition:  HasGitHubConnection = EnableGitHubConnectionAccess == "true"
  └── AWS::Include → modules/management-roles/pipeline-mgmt-role.yml
        └── NEW conditional IAM statement (Fn::If HasGitHubConnection):
              PassConnection + UseConnection + GetConnection + GetConnectionToken + ListTagsForResource
              (codestar-connections AND codeconnections namespaces)
              Resource: Fn::ImportValue "${OrgPrefix}-GitHub-Connection-Arn"
              Condition: codestar-connections:PassedToService = codepipeline.amazonaws.com

template-pipeline-github.yml  (developer, deployed BY the deployer role)
  └── unchanged — Source action passes GitHubConnectionArn; runtime role keeps UseConnection
```

The deployer role module already receives `OrgPrefix` from its parent, so no new **module parameter** is required — only a new **condition** (`HasGitHubConnection`) is added to the module contract.

## Components and Changes

### 1. Module: `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`

Add one entry to the inline policy's `Statement` list, wrapped in `Fn::If` so it is omitted entirely when the condition is false. Place it alongside the other code-service statements (near `ManageCodePipelineByResourcePrefix` / `ManageCodeBuildByResourcePrefix`).

```yaml
      - Fn::If:
        - HasGitHubConnection
        - Sid: PassGitHubConnectionForPipelines
          Effect: Allow
          Action:
          - codestar-connections:PassConnection
          - codestar-connections:UseConnection
          - codestar-connections:GetConnection
          - codestar-connections:GetConnectionToken
          - codestar-connections:ListTagsForResource
          - codeconnections:PassConnection
          - codeconnections:UseConnection
          - codeconnections:GetConnection
          - codeconnections:GetConnectionToken
          - codeconnections:ListTagsForResource
          Resource:
          - Fn::ImportValue:
              Fn::Sub: "${OrgPrefix}-GitHub-Connection-Arn"
          Condition:
            StringEquals:
              codestar-connections:PassedToService: codepipeline.amazonaws.com
        - Ref: "AWS::NoValue"
```

Contract comment block updates (top of the module):
- Add `HasGitHubConnection` to the required parent **conditions** list.
- Note: when `HasGitHubConnection` is true, the parent's `OrgPrefix` must resolve a valid `${OrgPrefix}-GitHub-Connection-Arn` export (from `account-wide-infrastructure.yml`); otherwise the stack fails at deploy (intended fail-loudly behavior).
- Note: connection ARNs are UUID-based and account-wide, so this statement is a deliberate exception to the `${Prefix}-*` ARN-scoping convention; it is instead scoped to the exact imported connection ARN and constrained by `PassedToService`.

Design rationale:
- **`Fn::If ... AWS::NoValue`** as a statement-list element: CloudFormation drops the element when the condition is false, so the rendered policy is byte-for-byte equivalent to today's for the default path (satisfies Req 2.2).
- **Both namespaces**: the service was renamed `codestar-connections` → `codeconnections`; IAM evaluates the `codestar-connections` namespace in the error, while the ARN is `codeconnections`. Granting both matches the repo's existing `UseConnection` pattern in the runtime role and avoids region/namespace drift (Req 1.1, 1.3).
- **Imported ARN resource**: tightest scope; single source of truth (Req 1.2).
- **`PassedToService` condition**: limits the pass to CodePipeline (Req 1.4).
- **Read actions** (`GetConnection`, `GetConnectionToken`, `ListTagsForResource`): included per decision Q7 to support connection validation/handshake during pipeline create/update.

### 2. Parent: `templates/v2/account/prefix-based-infrastructure.yml`

**New parameter** (grouped under a new metadata label):

```yaml
  EnableGitHubConnectionAccess:
    Type: String
    Description: "Set to 'true' to grant this prefix's Pipeline Management service role permission to pass and use the account-wide GitHub CodeConnections connection (required to deploy template-pipeline-github.yml). Requires OrgPrefix to be set and the account-wide GitHub connection (GitHubOrg) to have been created, because the connection ARN is imported from the account-wide export '<OrgPrefix>-GitHub-Connection-Arn'. Leave 'false' for prefixes that do not deploy GitHub-sourced pipelines."
    Default: "false"
    AllowedValues: ["true", "false"]
    ConstraintDescription: "Must be 'true' or 'false'."
```

**New condition:**

```yaml
  HasGitHubConnection: !Equals [!Ref EnableGitHubConnectionAccess, "true"]
```

**Metadata grouping** — add a new group after "Resources to Attach Managed Policies To" (or adjacent to the pipeline-management params):

```yaml
      -
        Label:
          default: "GitHub Connection Access"
        Parameters:
          - EnableGitHubConnectionAccess
```

**Header** — date-bump the `# Version:` comment to the current date; this template is dev-mode (v2.0.1 → the repo treats account/prefix templates as development per CHANGELOG, PATCH handling per version-control steering). Do not change the MAJOR/MINOR; a date-only bump is sufficient for an additive change in dev-mode. (Confirm during implementation whether a PATCH increment applies given the current header shows `v2.0.1`; see Decision Note below.)

**cfn-lint**: existing `ignore_checks` already include `E6101`, `W2001`, `W8001`, which cover the new condition consumed by `AWS::Include`. No change needed.

> **Decision Note (version):** The header currently reads `v2.0.1` (PATCH = 1 > 0), which per `template-version-control.md` is production mode where non-breaking changes auto-increment PATCH. However, the CHANGELOG narrative repeatedly labels account/prefix templates as development mode and applies account-wide changes in place. This is a conflict to confirm with the maintainer during implementation: either (a) bump PATCH to `v2.0.2` with today's date (strict reading of the version header), or (b) date-only bump if treating as dev-mode. Default assumption for tasks: **bump PATCH to v2.0.2** since the header shows PATCH > 0 and the change is additive/non-breaking. The changelog entry will reflect whichever is chosen.

### 3. Documentation

- `docs/templates/v2/account/prefix-based-infrastructure-README.md`: document `EnableGitHubConnectionAccess` (parameter table + a note on the `OrgPrefix`/account-wide-connection prerequisite and fail-loudly behavior), and add the new IAM statement to the role's documented permissions.
- `docs/templates/v2/account/account-wide-infrastructure-README.md`: add a cross-reference under the `GitHubConnectionArn` export noting it is consumed by the prefix Pipeline Management role when `EnableGitHubConnectionAccess="true"`.
- `docs/templates/v2/pipeline/template-pipeline-github-README.md`: clarify the two-role model (deployer vs runtime) and add the prerequisite that the prefix must have been provisioned with `EnableGitHubConnectionAccess="true"` before a GitHub pipeline can deploy.
- Preserve all existing blockquotes per documentation steering.

### 4. CHANGELOG

Add under `v0.0.45 (unreleased)`:

```markdown
### Added
- **Opt-in GitHub Connection Access for Pipeline Management Role** [Spec: 0-0-45-codestar-connection-pipeline-permissions](.kiro/specs/0-0-45-codestar-connection-pipeline-permissions/)
  - Account: prefix-based-infrastructure.yml <ver> - Added `EnableGitHubConnectionAccess` parameter and `HasGitHubConnection` condition
  - Modules: pipeline-mgmt-role.yml - Added conditional `codestar-connections`/`codeconnections` PassConnection + read/use statement scoped to the imported `${OrgPrefix}-GitHub-Connection-Arn`, guarded by `PassedToService: codepipeline.amazonaws.com`

### Fixed
- **GitHub Pipeline deploy failed with `codestar-connections:PassConnection` AccessDenied** [Spec: 0-0-45-codestar-connection-pipeline-permissions](.kiro/specs/0-0-45-codestar-connection-pipeline-permissions/) - The prefix Pipeline Management service role lacked permission to pass the account-wide GitHub connection to CodePipeline when creating `template-pipeline-github.yml`; now grantable per prefix via `EnableGitHubConnectionAccess`
```

## Data / Interface Changes

| Item | Type | Change | Breaking? |
|------|------|--------|-----------|
| `EnableGitHubConnectionAccess` | Parameter (prefix-based) | New, optional, default `"false"` | No |
| `HasGitHubConnection` | Condition (prefix-based + module contract) | New | No |
| `PassGitHubConnectionForPipelines` | IAM statement (module) | New, conditional | No |
| Export `${OrgPrefix}-GitHub-Connection-Arn` | Account-wide output | Now consumed via import when toggle on | No (export unchanged) |

No parameters renamed/removed, no outputs/exports changed, no resource logical IDs changed.

## Error Handling / Fail-Loudly

- The gating condition tests only `EnableGitHubConnectionAccess == "true"`. When true with a missing export (empty `OrgPrefix`, or account-wide GitHub connection never created), CloudFormation fails the prefix stack at deploy with an unresolved `Fn::ImportValue` error. This is intentional (Req 3) and surfaces the misconfiguration immediately.
- When false (default), no connection statement is emitted and no import is attempted; deployment behaves exactly as before.

## Testing Strategy

Per the workspace testing guidelines, prioritize fast, deterministic checks over property-based tests:

1. **cfn-lint (primary)** — run the repository pytest harness (`cfn_linter`) against `prefix-based-infrastructure.yml`. Confirms the template parses, the new parameter/condition are valid, and `AWS::Include` suppressions hold. Modules are validated indirectly as part of parent linting.
2. **Rendered-policy sanity (manual/review)** — confirm that with `EnableGitHubConnectionAccess="false"` the policy statement list is unchanged (no connection statement), and with `"true"` the statement appears with the imported-ARN resource and `PassedToService` condition. This is a review-time verification against the design, not an automated property test.
3. **No new property-based tests** — this change is a controlled, concrete IAM statement addition; unit/lint coverage is sufficient per `testing-guidelines`.

## Open Items to Confirm During Implementation

1. **Version increment for `prefix-based-infrastructure.yml`** — PATCH bump to `v2.0.2` vs date-only (see Decision Note). Default: PATCH bump.
2. **Metadata group name** — `"GitHub Connection Access"` proposed; confirm naming fits repo conventions.
