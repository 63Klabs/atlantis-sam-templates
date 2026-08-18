# Requirements Document

**Feature:** Cross-Account Serverless CI/CD Promotion (with Promotion & Release Approval)

**Spec:** `0-0-40-pipeline-with-promotion-approval`
**Repository target version:** v0.0.40 (unreleased)
**Status:** Draft for Review
**Date:** 2026-08-14

**Source documents:**
- [PRELIMINARY.md](./PRELIMINARY.md) — original feature proposal
- [QUESTIONS.md](./QUESTIONS.md), [QUESTIONS-2.md](./QUESTIONS-2.md), [QUESTIONS-3.md](./QUESTIONS-3.md), [QUESTIONS-4.md](./QUESTIONS-4.md) — resolved design decisions

---

## Introduction

This feature extends the Atlantis CI/CD framework to promote a validated git commit from one deployment stage to the next — across AWS accounts (DEV/TEST/PROD topology) or within a single account — using a controlled, auditable, and repeatable process. Promotion works by handing off the **pinned source commit** (an `source.zip` archive plus an audit manifest) through an S3 "promotions" prefix in the **receiving account's** account-wide artifacts bucket. The receiving pipeline is triggered by the arrival of that archive and performs a full build/deploy from source in the target account context.

The design is additive and backward compatible: all new behavior is disabled by default on the three existing pipeline templates, and a new promotion-triggered pipeline template is introduced for receiving stages.

### Chosen Architecture (locked)

- **Trigger model (Option A):** The Promote stage writes `source.zip` to a **stable, per-target key** the downstream pipeline watches. Because the account-wide bucket is versioned, overwriting that key fires an EventBridge event that starts the receiving pipeline, whose S3 Source action emits `source.zip` as its SourceArtifact. The build then behaves identically to a normal build. The commit SHA is carried in the **audit manifest and S3 object version**, not in the object key. Rollback is achieved by re-writing a prior archive to the stable key (via bucket versioning).
- **Manifest:** `promote.json` is **write-only audit** — nothing reads it at runtime. One rolling file per target key; history preserved by S3 versioning.
- **Per-account buckets:** The receiving account owns the promotion bucket (its account-wide artifacts bucket), the receiving pipeline, all worker roles, and the CloudFormation service role. The sender writes cross-account into the receiver's bucket under `promotions/*`.
- **Cross-region capable.** `PromoteTargetRegion` selects the target region (defaults to the current region). The only cross-region operation is the sender's S3 write into the receiving-region bucket; the receiving pipeline, its S3 source, and the EventBridge trigger live entirely in the target region.

### Templates and Modules Affected

**Existing templates modified (additive, non-breaking):**
- `templates/v2/pipeline/template-pipeline.yml` (v2.0.22 → v2.0.23)
- `templates/v2/pipeline/template-pipeline-github.yml` (v2.0.4 → v2.0.5)
- `templates/v2/pipeline/template-pipeline-build-only.yml` (v2.0.6 → v2.0.7)
- `templates/v2/account/account-wide-infrastructure.yml` (stays v0.0.0, development mode)

**New template:**
- `templates/v2/pipeline/template-pipeline-s3-source.yml` (v0.0.0)

**New modules (`templates/v2/modules/pipeline/`):**
- `promote-project.yml`, `promote-service-role.yml`, `promote-log-group.yml`, `promotion-source-event-rule.yml`, `promotion-source-event-service-role.yml`

**Modules modified in place (unversioned):**
- `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`
- `templates/v2/modules/account-wide/s3-artifacts-bucket.yml` (EventBridge notifications)

**Explicitly unchanged:** `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` and `templates/v2/account/prefix-based-infrastructure.yml` (existing grants already cover the new resources).

---

## Glossary

| Term | Meaning |
|---|---|
| **Origin/sending pipeline** | A pipeline built from an existing template (`template-pipeline.yml`, `-github.yml`, `-build-only.yml`) that adds an Approve-to-Promote + Promote stage. |
| **Receiving/promoted-artifact pipeline** | A pipeline built from the new `template-pipeline-s3-source.yml`, triggered by an S3 promotion archive. |
| **Promotion bucket** | The **receiving** account's account-wide artifacts bucket (`[org-]cf-artifacts-<acct>-<region>-an`), which holds inbound promotions under `promotions/*`. |
| **Stable trigger key** | `promotions/<prefix>-<projectId>/<stageId>/source.zip` — the object the receiving pipeline watches. |
| **Manifest** | `promotions/<prefix>-<projectId>/<stageId>/promote.json` — audit record written alongside the archive. |
| **Approve-to-Promote** | Manual approval gate on the sending side, before the Promote stage. Controlled by `PromoteApprovalRequired`. |
| **Approve-Release** | Manual approval gate on the receiving side, after Source and before Build. Controlled by `ReleaseApprovalRequired`. |

---

## Requirements

### Requirement 1: Commit-archive promotion handoff (Option A)

**User Story:** As a release engineer, I want a validated commit to be handed to the next stage as a source archive in S3, so that the downstream pipeline can rebuild deterministically from the exact promoted commit.

#### Acceptance Criteria

1. WHEN the Promote stage runs, the system SHALL upload the pipeline's existing SourceArtifact as `source.zip` to the promotion bucket at the stable key `promotions/<Prefix>-<ProjectId>/<PromoteTargetStageId>/source.zip`.
2. WHEN the Promote stage uploads `source.zip`, the system SHALL NOT re-clone the repository or run `git archive`; it SHALL reuse the SourceArtifact already present in the pipeline execution.
3. WHEN the Promote stage runs, the system SHALL write an audit manifest `promote.json` to `promotions/<Prefix>-<ProjectId>/<PromoteTargetStageId>/promote.json` in the same bucket.
4. WHERE the promotion bucket has versioning enabled, the system SHALL rely on S3 object versioning (not per-SHA object keys) to preserve promotion history and enable rollback.
5. WHEN a previously promoted archive must be redeployed (rollback), THEN re-writing that archive to the stable key SHALL re-trigger the receiving pipeline, subject to the same receiving-side approval gate.
6. The commit SHA SHALL NOT appear in the object key; it SHALL be recorded in the manifest and available via the S3 object version.

### Requirement 2: Commit SHA identification

**User Story:** As an auditor, I want each promotion associated with the exact source commit, so that I can trace what was deployed.

#### Acceptance Criteria

1. WHEN the Promote stage builds the manifest, the system SHALL capture the resolved source commit SHA (from `CODEBUILD_RESOLVED_SOURCE_VERSION` or the pipeline source revision).
2. The system SHALL store the full 40-character SHA in the manifest.
3. WHERE a short form is displayed (e.g., notifications), the system SHALL use the 7-character short SHA.
4. WHEN the source is GitHub via CodeConnections, the system SHALL treat the CodeConnections source revision SHA identically to the CodeCommit commit SHA.

### Requirement 3: Approve-to-Promote gate and Promote stage on existing templates

**User Story:** As a release engineer, I want an optional approval + promote step added to the existing pipelines, so that I can hand off a build to the next stage without breaking current pipelines.

#### Acceptance Criteria

1. The system SHALL add optional Approve-to-Promote and Promote stages to `template-pipeline.yml`, `template-pipeline-github.yml`, and `template-pipeline-build-only.yml`.
2. WHERE `PromoteTargetStageId` is a non-empty string, the system SHALL include the Promote stage in the pipeline; WHERE it is empty, the system SHALL include neither the Promote stage nor the Approve-to-Promote gate.
3. WHERE `PromoteTargetStageId` is non-empty AND `PromoteApprovalRequired` is `true`, the system SHALL insert the Approve-to-Promote manual approval action immediately before the Promote stage.
4. WHERE `PromoteTargetStageId` is non-empty AND `PromoteApprovalRequired` is `false`, the system SHALL include the Promote stage with no preceding approval action.
5. FOR `template-pipeline.yml` and `template-pipeline-github.yml`, the stage order SHALL be `Source → Build → Deploy → [PostDeploy] → [Approve-to-Promote] → [Promote]`.
6. FOR `template-pipeline-build-only.yml`, the stage order SHALL be `Source → Build → [Approve-to-Promote] → [Promote]`.
7. WHEN all promotion parameters are left at their defaults (promotion disabled), the deployed pipeline SHALL be structurally identical to the pre-feature pipeline (no new stages, no new resources that alter existing behavior).
8. The approval action used for the sending gate SHALL be named `ApproveToPromote` so it is programmatically detectable.

### Requirement 4: New promotion-triggered pipeline template

**User Story:** As a platform engineer, I want a single receiving pipeline template that is triggered by a promotion archive, so that beta/prod (and any number of stages) can be deployed from a promoted commit with the same build behavior as the origin.

#### Acceptance Criteria

1. The system SHALL provide a new template `templates/v2/pipeline/template-pipeline-s3-source.yml` at version v0.0.0.
2. The template SHALL define a Source stage whose provider is S3, reading `promotions/<Prefix>-<ProjectId>/<StageId>/source.zip` from `S3ArtifactsBucket` and emitting it as the SourceArtifact.
3. The template SHALL define a Build stage whose behavior is identical to the existing pipeline Build stage (same CodeBuild environment variables, buildspec resolution, and image), differing only in that the source is the S3 archive.
4. The template SHALL include a Deploy stage by default, and SHALL make the Deploy stage optional/skippable via a parameter (default: included) to support build-only-style workloads.
5. The template SHALL support an optional PostDeploy stage using the same conditional pattern as the existing templates.
6. The template SHALL support its own optional Approve-to-Promote + Promote stages (chained promotion, e.g., `beta → prod`) using the same rules as Requirement 3.
7. The template SHALL use a single `S3ArtifactsBucket` parameter for both its S3 Source location and its CodePipeline `ArtifactStore`; it SHALL NOT define a separate promotion-source bucket parameter.
8. WHERE the receiving pipeline watches its key, it SHALL derive the key from its own `Prefix`/`ProjectId`/`StageId` (it is the target).

### Requirement 5: Approve-Release gate on the receiving template

**User Story:** As a stage owner, I want to require approval before an incoming promoted artifact is built and deployed in my environment, so that I control what is released into my stage.

#### Acceptance Criteria

1. The new template SHALL provide a `ReleaseApprovalRequired` parameter (allowed values `true`/`false`, default `true`).
2. WHERE `ReleaseApprovalRequired` is `true`, the system SHALL insert an Approve-Release manual approval action after the Source stage and before the Build stage (`Source → Approve-Release → Build → ...`).
3. WHERE `ReleaseApprovalRequired` is `false`, the system SHALL build and deploy incoming promotions automatically (`Source → Build → ...`).
4. The approval action used for the receiving gate SHALL be named `ApproveRelease` so it is programmatically detectable.

### Requirement 6: Approval flags, defaults, and consequence warnings

**User Story:** As a security-conscious operator, I want approval gates enabled by default with clear warnings, so that fully-ungated promotion is a deliberate, informed choice.

#### Acceptance Criteria

1. The sending gate parameter SHALL be named `PromoteApprovalRequired` (allowed values `true`/`false`, default `true`).
2. The receiving gate parameter SHALL be named `ReleaseApprovalRequired` (allowed values `true`/`false`, default `true`).
3. The `PromoteApprovalRequired` parameter description SHALL explicitly state that setting it to `false` removes the human gate and promotes automatically, and that if the receiving pipeline also has `ReleaseApprovalRequired=false` the artifact will build and deploy in the target environment with no human review at any point, including into PROD stages.
4. The `ReleaseApprovalRequired` parameter description SHALL explicitly state that setting it to `false` auto-releases every incoming promotion, and that combined with an upstream `PromoteApprovalRequired=false` this yields a fully ungated path into the environment.
5. A fully-automated, zero-gate promotion path SHALL require an operator to explicitly set both `PromoteApprovalRequired=false` (sender) and `ReleaseApprovalRequired=false` (receiver).

### Requirement 7: Cross-account promotion bucket policy

**User Story:** As an account administrator, I want to allow a specific set of sending accounts to write promotions into my account-wide artifacts bucket, so that cross-account handoff works while preserving least privilege.

#### Acceptance Criteria

1. The system SHALL add an optional `PromotionSourceAccountIds` parameter (type `CommaDelimitedList`, default empty) to `account-wide-infrastructure.yml` and consume it in `s3-artifacts-bucket-policy.yml`.
2. WHERE `PromotionSourceAccountIds` is empty, the system SHALL omit the entire cross-account statement, preserving existing behavior exactly.
3. WHERE `PromotionSourceAccountIds` is non-empty, the system SHALL add one bucket policy statement whose `Principal.AWS` is the list of supplied account IDs (account roots) and whose `Condition` uses `StringLike` on `aws:PrincipalArn` matching `arn:aws:iam::*:role/*-PromoteServiceRole`.
4. The cross-account statement SHALL grant write (`s3:PutObject`) and scoped read (`s3:GetObject`, `s3:GetObjectVersion`) actions, restricted to the `promotions/*` key prefix only.
5. The cross-account statement SHALL NOT grant access to any principal other than roles matching `*-PromoteServiceRole`, and SHALL NOT grant access outside the `promotions/*` prefix.
6. The design SHALL verify the bucket's object ownership setting (Bucket Owner Enforced / ACLs disabled) so that objects written cross-account are owned by the receiving account; WHERE ownership is not enforced, the Promote upload SHALL set `bucket-owner-full-control`.

### Requirement 8: EventBridge trigger for the receiving pipeline

**User Story:** As a platform engineer, I want the receiving pipeline to start automatically when a promotion archive arrives, so that promotion is hands-off after approval.

#### Acceptance Criteria

1. The system SHALL add an optional capability to `s3-artifacts-bucket.yml` to enable EventBridge notifications on the account-wide artifacts bucket, gated behind an opt-in parameter so existing deployments are unaffected by default.
2. The system SHALL provide a `promotion-source-event-rule.yml` module defining an `AWS::Events::Rule` that matches S3 object-created events for the receiving pipeline's stable trigger key and targets the receiving pipeline.
3. The system SHALL provide a `promotion-source-event-service-role.yml` module defining the IAM role EventBridge assumes to call `codepipeline:StartPipelineExecution` on the receiving pipeline only.
4. WHEN an object is written to the receiving pipeline's stable trigger key (including cross-account writes), THEN the EventBridge rule SHALL start the receiving pipeline.
5. The event rule and its role SHALL follow the naming and conditional patterns of the existing `source-event-rule.yml` / `source-event-service-role.yml` modules.

### Requirement 9: Promote service role (sole cross-account writer)

**User Story:** As a security reviewer, I want only the Promote stage to be able to write promotions, so that the Build and PostDeploy stages cannot submit artifacts to other accounts.

#### Acceptance Criteria

1. The system SHALL provide a dedicated `promote-service-role.yml` module creating an IAM role named `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteServiceRole`.
2. The PromoteServiceRole SHALL be granted `s3:PutObject`, `s3:GetObject`, and `s3:GetObjectVersion` on `arn:aws:s3:::<PromoteTargetBucket>/promotions/*` only.
3. The system SHALL NOT add cross-account promotion write permissions to `CodeBuildServiceRole` or `PostDeployServiceRole`.
4. The role SHALL follow existing worker-role conventions (path, permissions boundary, trust policy for `codebuild.amazonaws.com`).
5. The Promote stage SHALL run as a dedicated CodeBuild project (`promote-project.yml`) using the PromoteServiceRole, with its own log group (`promote-log-group.yml`).
6. The Promote CodeBuild project SHALL use a framework-owned inline buildspec; it SHALL NOT require or support an app-repo buildspec override for promotion.

### Requirement 10: Target resolution parameters

**User Story:** As a release engineer, I want to specify the promotion target concisely, so that the same template works for cross-account and same-account promotion across arbitrary stages.

#### Acceptance Criteria

1. The system SHALL add these parameters to the sending templates (and to the new template for chained promotion): `PromoteTargetStageId`, `PromoteTargetAccountId`, `PromoteTargetRegion`, `PromoteTargetBucket`, `PromoteApprovalRequired`.
2. The system SHALL NOT add a `PromoteTargetDeployEnvironment` parameter; the receiving stack's own `DeployEnvironment` is authoritative, and `target_deploy_env` SHALL be omitted from the manifest.
3. WHERE `PromoteTargetAccountId` is empty, the system SHALL treat the promotion as same-account (target account = current account).
4. WHERE `PromoteTargetRegion` is empty, the system SHALL use the current region; WHERE non-empty, the system SHALL target the specified region (enabling cross-region promotion).
5. WHERE `PromoteTargetBucket` is empty, the system SHALL derive the bucket name as `<S3BucketNameOrgPrefix->cf-artifacts-<PromoteTargetAccountId>-<PromoteTargetRegion>-an`, using the current template's `S3BucketNameOrgPrefix` (identical across accounts per Assumption 1) and the resolved target account/region.
6. The promotion parameters SHALL be grouped in an `AWS::CloudFormation::Interface` metadata group positioned after the Post Deploy parameter group.
7. Promotion SHALL assume identical `Prefix` and `ProjectId` across the sending and receiving accounts; the sender's `PromoteTargetStageId` SHALL equal the receiver's `StageId`.

### Requirement 11: Promotion manifest (audit record)

**User Story:** As an auditor, I want a durable record of every promotion, so that I can review what was promoted, from where, and when.

#### Acceptance Criteria

1. The manifest SHALL be JSON written to `promotions/<Prefix>-<ProjectId>/<PromoteTargetStageId>/promote.json`.
2. The manifest SHALL include at minimum: `project`, `prefix`, `git_sha` (full), `git_sha_short`, `source_archive_key`, `promoted_from_stage`, `target_stage`, `promoted_at`, `source_account_id`, `target_account_id`, `target_region`, `target_bucket`, `source_pipeline_execution_id`, and `post_deploy_passed` (meaningful only when PostDeploy ran).
3. The manifest SHALL be a single rolling file per target key; promotion history SHALL be preserved via S3 object versioning.
4. The manifest SHALL be write-only audit; no pipeline stage SHALL read the manifest at runtime.
5. WHERE approver identity is not programmatically available from native approvals, the manifest MAY omit or leave blank a `promoted_by` field; approval history in CodePipeline SHALL be considered sufficient audit of the approver.

### Requirement 12: Promotion object lifecycle / retention

**User Story:** As an account administrator, I want promotion archives retained on a defined schedule, so that rollback is possible within a known window without unbounded storage growth.

#### Acceptance Criteria

> **Design note (S3 limitation):** S3 resolves overlapping lifecycle rules in favor of the shorter/expiration action and cannot exclude a prefix from a whole-bucket rule, so a `promotions/*`-scoped rule cannot lengthen retention beyond the existing whole-bucket rule. This feature therefore adjusts the whole-bucket rule (Option 3). The full analysis and future alternatives are recorded in [`.kiro/specs/future-s3-artifact-lifecycles/note.md`](../future-s3-artifact-lifecycles/note.md).

1. The system SHALL raise the account-wide artifacts bucket's existing `NoncurrentVersionExpirationInDays` from 30 to 365 (bucket-wide), giving promoted archives a 365-day rollback window via S3 object versioning.
2. The system SHALL retain the documented intent that current promotion objects (`source.zip` and `promote.json`) are not expired; it is ACKNOWLEDGED that the existing bucket-wide 395-day current-version expiration (`ExpirationInDays: 395`) remains in effect and overrides this intent (current promotion objects expire at 395 days). This limitation SHALL be documented for future resolution in `.kiro/specs/future-s3-artifact-lifecycles/note.md`.
3. The bucket-wide 365-day noncurrent-version retention SHALL apply to all objects in the bucket, including `source.zip` and `promote.json`.
4. The system SHALL NOT add a separate `promotions/*`-scoped lifecycle rule (it cannot achieve the intended retention; see the design note above).
5. The lifecycle change SHALL be additive to `account-wide-infrastructure.yml` (which remains in development mode, v0.0.0); the storage-cost tradeoff of retaining all noncurrent artifact versions for 365 days is accepted for this release.

### Requirement 13: Approval notifications

**User Story:** As an approver, I want to be notified when an approval is pending with the relevant context, so that I can act from the AWS console.

#### Acceptance Criteria

1. The manual approval actions SHALL publish to the existing `PipelineNotificationTopic` (reusing the current email subscription); the system SHALL NOT create a separate approval SNS topic or email list.
2. The approval notification SHALL include project name, prefix, stage, git SHA (short), pipeline execution ID, and a link to the pipeline execution.
3. The approval notification SHALL provide the CodePipeline execution console link; it SHALL NOT be required to construct a commit-diff/compare URL.
4. Approval and rejection SHALL be recorded in CodePipeline execution history; on rejection, the pipeline SHALL stop and no promotion archive or manifest SHALL be written.

### Requirement 14: Approval-audit CLI documentation

**User Story:** As an operations administrator, I want copy-paste CLI commands to find pipelines with approval gates disabled, so that I can govern promotion safety across our accounts.

#### Acceptance Criteria

1. The system SHALL document the approval-audit CLI in `docs/admin-ops/`.
2. The documentation SHALL provide three one-line, copy-paste commands (AWS CLI with pipes/`jq`):
   1. Pipelines that have a Promote stage but lack the `ApproveToPromote` action (`PromoteApprovalRequired=false` in effect).
   2. Promoted-artifact pipelines that lack the `ApproveRelease` action before Build (`ReleaseApprovalRequired=false` in effect).
   3. Pipelines matching either condition.
3. The commands SHALL detect state by inspecting deployed pipeline structure via `aws codepipeline list-pipelines` and `aws codepipeline get-pipeline` (detection method A), keying on the presence/absence of the named `Manual` approval actions.
4. Command 1 SHALL flag only pipelines that actually contain a Promote stage; pipelines that do not promote SHALL NOT be flagged.
5. The commands SHALL restrict matches to Atlantis pipelines by filtering on the resource tag `Atlantis=pipeline-infrastructure` (applied to all deployed Atlantis pipelines via stack-tag propagation), to avoid false positives from unrelated pipelines.
6. The design SHALL confirm the `Atlantis=pipeline-infrastructure` tag is queryable on deployed pipelines (e.g., via `aws codepipeline list-tags-for-resource` or the Resource Groups Tagging API) and use that mechanism to enumerate candidate pipelines.

### Requirement 15: Modularity and non-breaking composition

**User Story:** As a maintainer, I want new functionality delivered as modules composed by parent templates, so that the repository's structure and backward compatibility are preserved.

#### Acceptance Criteria

1. New supporting resources SHALL be delivered as `AWS::Include` modules under `templates/v2/modules/pipeline/`: `promote-project.yml`, `promote-service-role.yml`, `promote-log-group.yml`, `promotion-source-event-rule.yml`, `promotion-source-event-service-role.yml`.
2. New pipeline stages (Approve-to-Promote, Promote, S3 Source, Approve-Release) SHALL be inline, conditionally-included stage blocks in the parent templates (following the existing `!If [..., stage, !Ref 'AWS::NoValue']` pattern), because pipeline stages are defined inline in this repository.
3. Modules SHALL follow the module standards: no logical ID / no `Resources:` wrapper, long-form intrinsic functions only, and a contract comment block declaring required parent parameters, conditions, and sibling logical IDs.
4. All modifications to existing modules (`s3-artifacts-bucket-policy.yml`, `s3-artifacts-bucket.yml`) SHALL be additive with defaults that preserve current behavior.
5. Parent templates consuming modules SHALL declare `S3ModuleLocation` and `S3ModuleNamespace` per the canonical definitions and add appropriate `cfn-lint` suppressions for `AWS::Include`.

### Requirement 16: Service role adequacy (no changes required)

**User Story:** As a platform engineer, I want the existing deployment service roles to already permit the new resources, so that no privileged role changes are bundled into this feature.

#### Acceptance Criteria

1. The system SHALL NOT modify `pipeline-mgmt-role.yml` or `prefix-based-infrastructure.yml`; the existing prefix-scoped grants (`events:*`, `codebuild:*`, `codepipeline:*`, `sns:*`, and worker-role IAM on `${Prefix}-Worker-*`) SHALL be relied upon to create the new Promote project, PromoteServiceRole, event rule, and approval actions.
2. Ownership responsibility SHALL be: the account administrator owns the account-wide bucket, its EventBridge enablement, and its cross-account policy; the pipeline management role owns the pipeline stack resources.
3. The design SHALL verify (as a review step) that creating a worker role whose inline policy references a cross-account bucket ARN requires no additional management-role permission.

### Requirement 17: Versioning and changelog

**User Story:** As a maintainer, I want versions and the changelog updated per repository standards, so that consumers can track and adopt changes safely.

#### Acceptance Criteria

1. The system SHALL increment `template-pipeline.yml` to v2.0.23, `template-pipeline-github.yml` to v2.0.5, and `template-pipeline-build-only.yml` to v2.0.7, each with the current date, as the first change to each template.
2. The system SHALL create `template-pipeline-s3-source.yml` at v0.0.0 (development mode).
3. The system SHALL keep `account-wide-infrastructure.yml` at v0.0.0 (development mode; PATCH=0, no auto-increment).
4. All changes SHALL be additive and default-off; the system SHALL NOT introduce breaking changes and SHALL NOT create new versioned template files (`-v2-1.yml`, etc.).
5. The system SHALL add a `## v0.0.40 - unreleased` section to `CHANGELOG.md` with entries per modified/added template, referencing this spec, without modifying existing changelog text.

### Requirement 18: Documentation

**User Story:** As an end user, I want complete documentation for the new and changed templates, so that I can configure promotion correctly.

#### Acceptance Criteria

1. The system SHALL create `docs/templates/v2/pipeline/template-pipeline-s3-source-README.md` following the end-user documentation structure (Overview, Parameters by group, Resources, Outputs, and relevant optional sections).
2. The system SHALL update the affected existing pipeline template READMEs to document the new promotion parameters, stages, and resources, preserving existing blockquotes and custom content.
3. The system SHALL update the pipeline category README to include the new template.
4. The system SHALL document the approval-audit CLI in `docs/admin-ops/`.
5. The system SHALL document the manual two-account integration test procedure in `docs/maintainer/`.
6. Documentation updates SHALL be the final task and SHALL apply only to templates actually modified or added.

### Requirement 19: Testing

**User Story:** As a maintainer, I want fast, reliable validation of the templates, so that changes are safe to release.

#### Acceptance Criteria

1. The system SHALL validate all changed and added templates with `cfn-lint`.
2. Testing SHALL prioritize fast unit-style checks over property-based tests, consistent with the repository testing guidelines.
3. The full test suite SHALL complete quickly (target under 30 seconds) and SHALL provide clear failure messages.
4. WHERE cross-account behavior cannot be validated in CI, the system SHALL document a manual two-account integration test in `docs/maintainer/` rather than attempt automated cross-account testing.
5. Temporary files created during validation SHALL be cleaned up.

---

## 3. Non-Functional Requirements and Constraints

1. **Backward compatibility:** With all promotion parameters at defaults, existing pipelines SHALL deploy and behave exactly as before this feature.
2. **Least privilege:** All new IAM permissions SHALL be scoped by action, resource ARN (naming convention), and (for cross-account) the `promotions/*` prefix and `*-PromoteServiceRole` principal pattern. No AWS managed full-access policies SHALL be used.
3. **Encryption:** The design SHALL preserve the existing SSE-S3 (AES256) encryption on the artifacts bucket; no KMS key sharing SHALL be introduced.
4. **Region:** Promotion SHALL support both same-region and cross-region targets. WHERE `PromoteTargetRegion` is non-empty, the system SHALL target that region; WHERE empty, it SHALL use the current region. Cross-region requires no additional components because the only region boundary is the sender's S3 write into the receiving-region bucket; the receiving pipeline, its S3 source, and the EventBridge trigger are wholly within the target region. The design SHALL confirm cross-region S3 writes (sender → receiving-region bucket) and same-region EventBridge delivery behave as expected.
5. **Naming conventions:** All resources SHALL follow `${Prefix}-${ProjectId}-${StageId}-<ResourceId>` and worker roles the `-Worker-` infix, per repository standards.
6. **Parameterized stages:** No stage identifiers SHALL be hard-coded in conditionals; DEV/TEST/PROD remain the only environment classifications, and promotion targets SHALL be driven by parameters.
7. **Module authoring:** All new/modified modules SHALL use long-form intrinsic functions and omit logical IDs, per module standards.

---

## 4. Out of Scope

1. Renaming existing pipeline artifact names to include the `Prefix` (tracked separately; excluded per R6a).
2. Automatic provisioning of the receiving-region account-wide bucket or module bucket (operators must ensure the regional prerequisites exist in the target region for cross-region promotion).
3. A Lambda-based trigger or manifest-driven runtime configuration (Options B/C were rejected in favor of Option A).
4. Automated cross-account integration testing in CI (documented manual procedure instead).
5. External/automated audit processing of the manifest (may be added by a future external process; the manifest is write-only audit here).
6. Changes to `pipeline-mgmt-role.yml` and `prefix-based-infrastructure.yml`.
7. Any app-repo buildspec override for the Promote stage.

---

## 5. Assumptions

1. `Prefix`, `ProjectId`, and `S3BucketNameOrgPrefix` are identical across the sending and receiving accounts for a given project.
2. The receiving account's account-wide artifacts bucket exists (deployed via `account-wide-infrastructure.yml`) and is versioned.
3. The receiving account hosts the promoted-artifact pipeline, its worker roles, and its CloudFormation service role.
4. Operators deploy these pipelines via the Atlantis `config.py`/`deploy.py` scripts (template instantiation itself is out of scope).
5. The account-wide artifacts bucket enforces Bucket Owner Enforced object ownership (to be verified in design; fallback is `bucket-owner-full-control` on upload).
