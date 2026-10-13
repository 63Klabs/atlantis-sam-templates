# Requirements: CodeStar/CodeConnections Pipeline Management Permissions

**Spec:** `0-0-45-codestar-connection-pipeline-permissions`
**Repository version:** v0.0.45 (unreleased)
**Status:** Draft for review

## Introduction

Deploying `template-pipeline-github.yml` fails because the prefix-based CloudFormation Pipeline Management service role (`${PrefixUpper}-CloudFormation-Service-Role-Pipeline-Management`) is not authorized to perform `codestar-connections:PassConnection` on the account-wide GitHub CodeConnections connection. When CloudFormation (acting as that deployer role) creates the `AWS::CodePipeline::Pipeline` resource whose Source action embeds a `ConnectionArn`, CodePipeline requires the caller to hold `PassConnection` on the connection — analogous to `iam:PassRole`. The deployer role currently grants no `codestar-connections` / `codeconnections` actions at all.

This feature adds an opt-in, least-privilege grant to the deployer role so a prefix can be authorized to pass and use the account-wide GitHub connection, without changing behavior for prefixes that do not deploy GitHub-sourced pipelines.

The account-wide GitHub connection already exists and is created and exported by `account-wide-infrastructure.yml` (export `${OrgPrefix}-GitHub-Connection-Arn`). The design decisions are locked in `PLAN.md` §5.

## Glossary

- **Deployer role** — `${PrefixUpper}-CloudFormation-Service-Role-Pipeline-Management`, defined in `modules/management-roles/pipeline-mgmt-role.yml`, assembled by `prefix-based-infrastructure.yml`. Assumed by CloudFormation at deploy time to create pipeline stacks.
- **Runtime role** — the inline `${Prefix}-Worker-${ProjectId}-${StageId}-CodePipelineServiceRole` in `template-pipeline-github.yml`, assumed by CodePipeline at execution time. Already holds `UseConnection`. Out of scope for change.
- **Connection** — the account-wide `AWS::CodeConnections::Connection` created by `account-wide-infrastructure.yml`, ARN exported as `${OrgPrefix}-GitHub-Connection-Arn`.

## Requirements

### Requirement 1 — Deployer role can pass the GitHub connection when enabled

**User story:** As an account administrator, I want the prefix Pipeline Management service role to be authorized to pass the account-wide GitHub connection to CodePipeline, so that developers under that prefix can successfully deploy `template-pipeline-github.yml`.

**Acceptance criteria:**

1. WHEN `EnableGitHubConnectionAccess` is `"true"` on the prefix-based deployment THEN the deployer role SHALL include an IAM statement allowing `codestar-connections:PassConnection` and `codeconnections:PassConnection`.
2. WHEN the grant is present THEN its `Resource` SHALL be scoped exactly to the account-wide connection ARN resolved via `Fn::ImportValue` of `${OrgPrefix}-GitHub-Connection-Arn` (no wildcard connection ARNs).
3. WHEN the grant is present THEN it SHALL also allow the read/use actions `UseConnection`, `GetConnection`, `GetConnectionToken`, and `ListTagsForResource` in both the `codestar-connections` and `codeconnections` namespaces.
4. WHEN the grant is present THEN it SHALL include a condition `StringEquals { codestar-connections:PassedToService: codepipeline.amazonaws.com }` restricting the pass target to CodePipeline.
5. WHEN a developer deploys `template-pipeline-github.yml` under a prefix provisioned with `EnableGitHubConnectionAccess="true"` and a valid connection THEN the stack SHALL create the `AWS::CodePipeline::Pipeline` without a `codestar-connections:PassConnection` AccessDenied error.

### Requirement 2 — Opt-in and backward compatible

**User story:** As an account administrator, I want the new permission to be opt-in per prefix, so that prefixes that do not host GitHub pipelines are not granted any additional access and existing deployments are unaffected.

**Acceptance criteria:**

1. The prefix-based deployment SHALL expose a new parameter `EnableGitHubConnectionAccess` of type String with `AllowedValues` `["true", "false"]` and `Default` `"false"`.
2. WHEN `EnableGitHubConnectionAccess` is `"false"` (including by default) THEN the deployer role SHALL render with no `codestar-connections` / `codeconnections` statements, identical to the current (pre-change) policy.
3. The change SHALL NOT rename, remove, or alter the type of any existing parameter, output, export, condition, or resource logical ID.
4. The change SHALL be additive only (new parameter, new condition, new conditional IAM statement); no existing permission SHALL be removed or narrowed.
5. The deprecated `template-service-role-pipeline.yml` assembler SHALL be left unchanged.

### Requirement 3 — Fail loudly on misconfiguration

**User story:** As an account administrator, I want enabling connection access without the prerequisites to fail immediately and visibly, so that a misconfiguration is obvious rather than silently granting nothing.

**Acceptance criteria:**

1. The gating condition SHALL be `HasGitHubConnection = (EnableGitHubConnectionAccess == "true")` and SHALL NOT additionally test whether `OrgPrefix` is non-empty.
2. WHEN `EnableGitHubConnectionAccess` is `"true"` AND the export `${OrgPrefix}-GitHub-Connection-Arn` does not exist (because `OrgPrefix` is empty or the account-wide GitHub connection was never created) THEN the prefix-based stack deployment SHALL fail at deploy time due to the unresolved `Fn::ImportValue`.

### Requirement 4 — Standards, documentation, and changelog

**User story:** As a maintainer, I want the change to follow repository module/parameter/versioning standards and to be documented, so that the templates stay consistent and discoverable.

**Acceptance criteria:**

1. The module `pipeline-mgmt-role.yml` SHALL use long-form intrinsic functions only (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::ImportValue`) and SHALL NOT introduce a logical ID or `Resources:` wrapper.
2. The module contract comment block SHALL be updated to list `HasGitHubConnection` as a required parent condition and to note the connection-ARN scoping exception to the `${Prefix}-*` convention and the `OrgPrefix` export dependency.
3. The new parameter SHALL be placed in an appropriate `AWS::CloudFormation::Interface` metadata group in `prefix-based-infrastructure.yml`, and the template header date SHALL be bumped (dev-mode v0.0.x; no PATCH increment).
4. Documentation SHALL be updated: `prefix-based-infrastructure-README.md`, `account-wide-infrastructure-README.md` (cross-reference the export consumer), and `template-pipeline-github-README.md` (deployer-role vs runtime-role prerequisites).
5. `CHANGELOG.md` SHALL have an entry under `v0.0.45 (unreleased)` referencing this spec, categorized under Fixed (missing PassConnection) and Added (`EnableGitHubConnectionAccess`).
6. The affected template(s) SHALL pass cfn-lint via the repository pytest harness, with any required `AWS::Include` suppressions (`E6101`, `W2001`, `W8001`) present.

## Out of Scope

- Changes to the runtime `CodePipelineServiceRole` in `template-pipeline-github.yml` (already has `UseConnection`; `PassConnection` is not required at execution time).
- Changes to the deprecated `template-service-role-pipeline.yml`.
- Support for more than one connection per prefix, or non-GitHub providers.
- Automating completion/authorization of the connection (remains a manual console step owned by the account-wide stack).
