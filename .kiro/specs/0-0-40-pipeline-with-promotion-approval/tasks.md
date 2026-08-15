# Implementation Plan: Cross-Account Serverless CI/CD Promotion

**Spec:** `0-0-40-pipeline-with-promotion-approval`
**References:** [requirements.md](./requirements.md), [design.md](./design.md)

## Overview

This plan implements cross-account serverless CI/CD promotion with an optional manual approval gate. Work proceeds bottom-up: shared modules are built first, then wired into the parent/origin templates that include them, followed by a new receiving template, testing, documentation, and the changelog.

The change set spans five areas:
- **Account-wide artifacts** — bucket lifecycle, ownership, EventBridge opt-in, and a cross-account write policy scoped to `promotions/*`.
- **New pipeline modules** — promote service role, promote CodeBuild project, promote log group, and the promotion-source EventBridge rule + service role.
- **Origin templates** — additive, default-off promotion (send) capability across `template-pipeline.yml`, `template-pipeline-github.yml`, and `template-pipeline-build-only.yml`.
- **Receiving template** — a new `template-pipeline-promoted-artifact.yml` triggered by an S3 promotion artifact.
- **Verification & docs** — cfn-lint, fast render/structure tests, end-user docs, an approval-audit CLI, and a manual two-account integration procedure.

All new pipeline parameters are additive and default-off, so existing deployments render identically until promotion is explicitly enabled.

## Notes

- Work top-to-bottom; later tasks depend on earlier ones (modules before the parent templates that include them).
- All new pipeline parameters are additive and default-off; verify backward compatibility after each template change.
- Modules use long-form intrinsics only and carry a contract comment block (module standards).
- Per the testing guidelines, prioritize fast unit-style render checks; property-based tests are optional and marked `(optional)`.

## Task Dependency Graph

```
0. Pre-flight verification ──┐  (no code deps; gates the work)
                             │
1. Version management ───────┤  (independent; first edit to each template)
                             │
2. Account-wide bucket/policy
   2.1 s3-artifacts-bucket ──┐
   2.2 s3-artifacts-policy ──┼──▶ 2.3 account-wide-infrastructure (parent)
                             │
3. New pipeline modules
   3.1 promote-service-role
   3.2 promote-project
   3.3 promote-log-group
   3.4 promotion-source-event-service-role
   3.5 promotion-source-event-rule
        │
        ├──────────────▶ 4. Origin templates (include 3.1–3.3)
        │                   4.1 params → 4.2 conditions → 4.3 includes
        │                   → 4.4 stages → 4.5 backward-compat check
        │
        └──────────────▶ 5. Receiving template (includes 3.1–3.5)
                            5.1 template → 5.2 conditions/includes
                            → 5.3 stages → 5.4 outputs

6. Testing ◀── depends on 2, 3, 4, 5
7. Documentation ◀── depends on 4, 5 (only modified/added templates)
8. Changelog ◀── depends on all of the above
```

Critical path: `3 → 4/5 → 6 → 7 → 8`. Sections 4 and 5 are independent of each other once section 3 is complete and may proceed in parallel.

Wave definitions (tasks in the same wave have no dependencies on each other and may run in parallel):

```json
{
  "waves": [
    { "id": 0, "tasks": ["0.1", "0.2", "1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "3.1", "3.2", "3.3", "3.4", "3.5"] },
    { "id": 1, "tasks": ["2.3", "4.1", "5.1"] },
    { "id": 2, "tasks": ["4.2", "5.2"] },
    { "id": 3, "tasks": ["4.3", "5.3"] },
    { "id": 4, "tasks": ["4.4", "5.4"] },
    { "id": 5, "tasks": ["4.5"] },
    { "id": 6, "tasks": ["6.1", "6.2", "6.3", "6.4"] },
    { "id": 7, "tasks": ["7.1", "7.2", "7.3", "7.4"] },
    { "id": 8, "tasks": ["8.1"] }
  ]
}
```

## Tasks

### 0. Pre-flight verification

- [ ] 0.1 Verify management-role adequacy (no changes expected)
  - Read `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` and confirm it already permits creating: a CodeBuild project (`${Prefix}-*-Promote`), a worker role (`${Prefix}-Worker-*-PromoteServiceRole`) with an inline policy referencing a cross-account bucket ARN, an EventBridge rule, and the EventBridge service role.
  - Record the finding in the PR/commit description. If a gap is found, STOP and raise it before widening the role.
  - _Requirements: 16.1, 16.3_

- [ ] 0.2 Verify the `Atlantis=pipeline-infrastructure` tag is queryable
  - Confirm deployed pipelines carry the tag (via stack-tag propagation) and can be enumerated with `aws resourcegroupstaggingapi get-resources` / `aws codepipeline list-tags-for-resource`. Note the exact query for use in Task 7.3.
  - _Requirements: 14.5, 14.6_

### 1. Version management (first edit to each template)

- [ ] 1.1 Bump `templates/v2/pipeline/template-pipeline.yml` header to `v2.0.23/<today>`
- [ ] 1.2 Bump `templates/v2/pipeline/template-pipeline-github.yml` header to `v2.0.5/<today>`
- [ ] 1.3 Bump `templates/v2/pipeline/template-pipeline-build-only.yml` header to `v2.0.7/<today>`
- [ ] 1.4 Confirm `templates/v2/account/account-wide-infrastructure.yml` stays `v0.0.0` (development mode; no auto-increment). New `template-pipeline-promoted-artifact.yml` will start at `v0.0.0`.
  - _Requirements: 17.1, 17.2, 17.3, 17.4_

### 2. Account-wide artifacts bucket and policy

- [ ] 2.1 Update `templates/v2/modules/account-wide/s3-artifacts-bucket.yml`
  - Change `NoncurrentVersionExpirationInDays` in the `ExpireObjects` rule from `30` to `365`; keep `ExpirationInDays: 395` and `AbortIncompleteMultipartUpload` unchanged.
  - Add `OwnershipControls: Rules: [{ ObjectOwnership: BucketOwnerEnforced }]`.
  - Add conditional `NotificationConfiguration` = `Fn::If [EnableArtifactsBucketEventBridge, { EventBridgeConfiguration: {} }, AWS::NoValue]`.
  - Update the module contract comment (new conditions consumed).
  - _Requirements: 7.6, 8.1, 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 2.2 Update `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`
  - Append a cross-account statement `AllowCrossAccountPromotionWrite`, wrapped in `Fn::If [HasPromotionSourceAccounts, {statement}, AWS::NoValue]`:
    - `Principal.AWS: !Ref PromotionSourceAccountIds`
    - Actions `s3:PutObject`, `s3:GetObject`, `s3:GetObjectVersion`
    - Resource `${S3ArtifactsBucketRegional.Arn}/promotions/*` only
    - `Condition: StringLike { aws:PrincipalArn: "arn:aws:iam::*:role/*-PromoteServiceRole" }`
  - Update the module contract comment (new parameter + condition consumed).
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 2.3 Update `templates/v2/account/account-wide-infrastructure.yml` parent
  - Add parameters `PromotionSourceAccountIds` (`CommaDelimitedList`, default `""`) and `EnableS3ArtifactsBucketEventBridge` (`String`, `true`/`false`, default `false`), grouped under a "Promotion" metadata group.
  - Add conditions `HasPromotionSourceAccounts` and `EnableArtifactsBucketEventBridge`.
  - Confirm cfn-lint `AWS::Include` suppressions are present.
  - _Requirements: 7.1, 8.1, 15.4, 15.5_

### 3. New pipeline modules

- [ ] 3.1 Create `templates/v2/modules/pipeline/promote-service-role.yml`
  - `AWS::IAM::Role`, condition `IsPromoteEnabledAndNotDev`, name `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteServiceRole`, trust `codebuild.amazonaws.com`, path + permissions boundary per convention.
  - Inline policy: manage its logs; read local `${S3ArtifactsBucket}` (input SourceArtifact); write/read `arn:aws:s3:::<resolved PromoteTargetBucket>/promotions/*` (`s3:PutObject`, `s3:GetObject`, `s3:GetObjectVersion`).
  - Contract comment block naming required parent params/conditions.
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 15.3_

- [ ] 3.2 Create `templates/v2/modules/pipeline/promote-project.yml`
  - `AWS::CodeBuild::Project`, condition `IsPromoteEnabledAndNotDev`, name `${Prefix}-${ProjectId}-${StageId}-Promote`, ServiceRole `PromoteServiceRole`, same image/compute as Build.
  - Environment variables per design §5.1 (PROMOTE_TARGET_*, resolved bucket/region/account, PROMOTION_KEY_PREFIX).
  - Inline `BuildSpec` (framework-owned): resolve SHA, zip `CODEBUILD_SRC_DIR` → `source.zip`, write `promote.json`, upload manifest first then `source.zip` last (with `--region` target). No app-repo override.
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 9.5, 9.6, 11.1, 11.2_

- [ ] 3.3 Create `templates/v2/modules/pipeline/promote-log-group.yml`
  - `AWS::Logs::LogGroup`, condition `IsPromoteEnabledAndNotDev`, name `/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Promote`, retention 90 (mirror `codebuild-log-group.yml`).
  - _Requirements: 9.5_

- [ ] 3.4 Create `templates/v2/modules/pipeline/promotion-source-event-service-role.yml`
  - `AWS::IAM::Role`, condition `IsNotDevelopment`, name `${Prefix}-Worker-${ProjectId}-${StageId}-PromotionSourceEventServiceRole`, trust `events.amazonaws.com`, single `codepipeline:StartPipelineExecution` on the receiving pipeline ARN (mirror `source-event-service-role.yml`).
  - _Requirements: 8.3_

- [ ] 3.5 Create `templates/v2/modules/pipeline/promotion-source-event-rule.yml`
  - `AWS::Events::Rule`, condition `IsNotDevelopment`, name `${Prefix}-${ProjectId}-${StageId}-PromotionSourceEvent`.
  - EventPattern: `aws.s3` / `Object Created`, `detail.bucket.name = [S3ArtifactsBucket]`, `detail.object.key = ["promotions/${Prefix}-${ProjectId}/${StageId}/source.zip"]`.
  - Target the receiving pipeline ARN with `PromotionSourceEventServiceRole`.
  - _Requirements: 8.2, 8.4, 8.5_

### 4. Origin templates — add promotion (send) capability

Apply 4.x to all three origin templates: `template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`.

- [ ] 4.1 Add promotion parameters + metadata group
  - Add `PromoteTargetStageId`, `PromoteApprovalRequired` (default `true`), `PromoteTargetAccountId`, `PromoteTargetRegion`, `PromoteTargetBucket` (all default `""` except approval).
  - Group under "Promotion (Send to Next Stage)" immediately after the Post Deploy group.
  - Write the `PromoteApprovalRequired` description with the explicit ungated-into-PROD warning.
  - _Requirements: 6.1, 6.3, 6.5, 10.1, 10.6_

- [ ] 4.2 Add conditions
  - `IsPromoteEnabled`, `IsPromoteApprovalRequired`, `IsPromoteEnabledAndApprovalRequired`, `IsPromoteEnabledAndNotDev`, `HasPromoteTargetAccount`, `HasPromoteTargetRegion`, `HasPromoteTargetBucket`.
  - _Requirements: 3.2, 3.3, 3.4, 10.3, 10.4, 10.5_

- [ ] 4.3 Include the new modules
  - Add `PromoteServiceRole`, `PromoteProject`, `PromoteLogGroup` via `AWS::Include` (exact sibling logical IDs).
  - _Requirements: 9.1, 9.5, 15.1, 15.2_

- [ ] 4.4 Add inline stages to `ProjectPipeline`
  - `ApproveToPromote` (Manual, named `ApproveToPromote`, `NotificationArn = PipelineNotificationTopic`, CustomData + ExternalEntityLink) gated on `IsPromoteEnabledAndApprovalRequired`.
  - `Promote` (CodeBuild `${Prefix}-${ProjectId}-${StageId}-Promote`, input = SourceArtifact) gated on `IsPromoteEnabled`.
  - Order: `... → [PostDeploy] → [ApproveToPromote] → [Promote]` (build-only: `Source → Build → [ApproveToPromote] → [Promote]`).
  - _Requirements: 3.1, 3.5, 3.6, 3.8, 13.1, 13.2, 13.3, 13.4_

- [ ] 4.5 Verify backward compatibility
  - With all promotion params at defaults, confirm the rendered pipeline is structurally identical to pre-change (no new stages/resources created; new module resources gated off).
  - _Requirements: 3.7, NFR #1_

### 5. New receiving template

- [ ] 5.1 Create `templates/v2/pipeline/template-pipeline-promoted-artifact.yml` (v0.0.0)
  - Header comment block, Metadata interface, standard parameter set minus `Repository`/`RepositoryBranch`/`GitHubConnectionArn`.
  - Add `ReleaseApprovalRequired` (default `true`, with auto-release warning), `DeployStageEnabled` (default `true`), and the `PromoteTarget*`/`PromoteApprovalRequired` set for chained promotion.
  - Module Source params + cfn-lint suppressions.
  - _Requirements: 4.1, 5.1, 6.2, 6.4, 10.1, 15.5_

- [ ] 5.2 Conditions + module includes
  - Add `IsReleaseApprovalRequired`, `IsDeployStageEnabled`, plus the promotion conditions from 4.2.
  - Include shared modules (CodeBuild project/role/log group, CloudFormation svc role, CodeDeploy svc role, PostDeploy set, notification set) and the new promote + promotion-source-event modules.
  - _Requirements: 4.5, 5.1, 8.2, 8.3_

- [ ] 5.3 Define `ProjectPipeline` stages
  - Source (S3): `S3Bucket = S3ArtifactsBucket`, `S3ObjectKey = promotions/${Prefix}-${ProjectId}/${StageId}/source.zip`, `PollForSourceChanges: false`.
  - `[ApproveRelease]` (Manual, named `ApproveRelease`) gated on `IsReleaseApprovalRequired`, between Source and Build.
  - Build (identical to existing), `[Deploy]` gated on `IsDeployStageEnabled`, `[PostDeploy]`, `[ApproveToPromote]`, `[Promote]` (chained).
  - `ArtifactStore.Location = S3ArtifactsBucket` (same bucket as S3 source).
  - _Requirements: 4.2, 4.3, 4.4, 4.6, 4.7, 4.8, 5.2, 5.3, 5.4_

- [ ] 5.4 Outputs
  - Pipeline console link, pipeline name, and the watched promotion key (for operator reference); conditional promote/release outputs as useful.
  - _Requirements: 4.1_

### 6. Testing

- [ ] 6.1 cfn-lint all changed/added templates
  - `template-pipeline.yml`, `-github.yml`, `-build-only.yml`, `template-pipeline-promoted-artifact.yml`, `account-wide-infrastructure.yml`.
  - _Requirements: 19.1_

- [ ] 6.2 Unit-style render/structure tests
  - Origin: defaults ⇒ no `Promote`/`ApproveToPromote`; `PromoteTargetStageId` set + approval `true` ⇒ both present in order; approval `false` ⇒ `Promote` only.
  - Receiving: `ReleaseApprovalRequired=false` ⇒ no `ApproveRelease`; `DeployStageEnabled=false` ⇒ no Deploy stage.
  - Bucket policy: empty `PromotionSourceAccountIds` ⇒ no cross-account statement; non-empty ⇒ statement present, `promotions/*` only, `*-PromoteServiceRole` condition.
  - Target-bucket derivation: org-prefix / no-org-prefix × same/cross account & region.
  - Lifecycle: `NoncurrentVersionExpirationInDays == 365`, `ExpirationInDays == 395`.
  - _Requirements: 3.7, 5.2, 5.3, 7.2, 7.3, 7.4, 10.5, 12.1, 19.2, 19.3_

- [ ] 6.3 (optional) Minimal property-based checks only where they add value beyond 6.2
  - _Requirements: 19.2_

- [ ] 6.4 Clean up any temporary render files produced by tests
  - _Requirements: 19.5_

### 7. Documentation (final; only for modified/added templates)

- [ ] 7.1 Create `docs/templates/v2/pipeline/template-pipeline-promoted-artifact-README.md`
  - Full end-user structure: Overview, Parameters by group, Resources, Outputs, plus Examples/Troubleshooting/Related as relevant.
  - _Requirements: 18.1_

- [ ] 7.2 Update existing pipeline READMEs + category README
  - Document new promotion parameters, stages (`ApproveToPromote`/`Promote`), and resources in the three origin template READMEs (preserve blockquotes/custom content); add the new template to the pipeline category README.
  - _Requirements: 18.2, 18.3_

- [ ] 7.3 Approval-audit CLI in `docs/admin-ops/`
  - Three copy-paste one-liners (enumerate by tag `Atlantis=pipeline-infrastructure`, then inspect `get-pipeline`): (1) has `Promote` stage but no `ApproveToPromote`; (2) has S3 source but no `ApproveRelease`; (3) either. Include the consequence context.
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [ ] 7.4 Manual two-account integration test in `docs/maintainer/`
  - Step-by-step procedure to validate cross-account promotion end-to-end (and a same-account variant).
  - _Requirements: 18.5, 19.4_

### 8. Changelog

- [ ] 8.1 Add `## v0.0.40 - unreleased` to `CHANGELOG.md` (append only; do not modify existing text)
  - Entries per modified/added template with versions, referencing this spec: pipeline v2.0.23 / github v2.0.5 / build-only v2.0.7 (Added: promotion send stages), new `template-pipeline-promoted-artifact.yml` v0.0.0 (Added), `account-wide-infrastructure.yml` (Changed: cross-account promotion policy, EventBridge opt-in, noncurrent retention 30→365).
  - _Requirements: 17.5_
