# Design Document: Cross-Account Serverless CI/CD Promotion

**Spec:** `0-0-40-pipeline-with-promotion-approval`
**Repository target version:** v0.0.40 (unreleased)
**Status:** Draft for Review
**Date:** 2026-08-14

**Related documents:** [requirements.md](./requirements.md), [PRELIMINARY.md](./PRELIMINARY.md), and the resolved decision logs [QUESTIONS.md](./QUESTIONS.md) → [QUESTIONS-4.md](./QUESTIONS-4.md).

---

## Overview

This design adds **stage-to-stage promotion** to the Atlantis pipeline framework. A validated commit built by an origin pipeline (e.g. `test`) is handed to a downstream pipeline (e.g. `beta`, then `prod`) — across AWS accounts or within one account — by writing the pinned source archive plus an audit manifest into the **receiving account's** S3 promotions area. Arrival of the archive triggers the receiving pipeline via EventBridge, which rebuilds and deploys from source in the target account context.

The design follows the repository's established patterns:
- **Plain CloudFormation** pipeline templates with a single inline `AWS::CodePipeline::Pipeline` (`ProjectPipeline`) resource; supporting resources pulled in as `AWS::Include` modules.
- **Additive, default-off** parameters on the three existing templates so deployed pipelines are unchanged unless promotion is explicitly configured.
- **New inline, conditionally-included stages** (using the existing `Fn::If [..., stage, AWS::NoValue]` pattern) plus **new modules** for the supporting resources.

### 1.1 Design decisions carried from the decision log

| # | Decision | Source |
|---|---|---|
| Option A | Stable trigger key + audit-only manifest; SHA in manifest/object version, not the key | Q1 |
| Reuse SourceArtifact | Promote re-uploads the pipeline SourceArtifact as `source.zip`; no re-clone | Q6 |
| Inline promote buildspec | Framework-owned; no app-repo override | Q7 |
| Dedicated PromoteServiceRole | Sole cross-account writer; Build/PostDeploy roles unchanged | R1 |
| Account list in bucket policy | `PromotionSourceAccountIds` (list) via Principal-list + single `StringLike` condition | R2 |
| Two independent approval gates | `PromoteApprovalRequired` (default true), `ReleaseApprovalRequired` (default true) | R5, T1 |
| Cross-region supported | `PromoteTargetRegion` selects region; boundary is only the S3 write | requirements NFR #4 |
| Audit CLI | Three commands in `docs/admin-ops/`, structure inspection, tag `Atlantis=pipeline-infrastructure` | T3, R14 |

### 1.2 Resolved design decision — DD-1 (see §7.3)

**DD-1 (Promotions retention) — RESOLVED to Option 3.** S3 resolves overlapping lifecycle rules in favor of the **shorter** expiration and cannot exclude a prefix from a whole-bucket rule, so a `promotions/*`-scoped rule cannot lengthen retention (see [AWS docs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-conflicts.html)). Per the decision, promotions stay in the account-wide artifacts bucket (preserving R3a) and the bucket's existing rule is adjusted: **`NoncurrentVersionExpirationInDays` is raised 30 → 365** (bucket-wide) to provide the 365-day rollback window. The current-version `ExpirationInDays: 395` is **kept as-is**, so the "current promotion object never expires" intent is documented but **not honored** (current promotion objects expire at 395 days). The tradeoff (all noncurrent artifact versions now retained 365 days) is accepted for this release, and the limitation + future alternatives are recorded in [`.kiro/specs/future-s3-artifact-lifecycles/note.md`](../future-s3-artifact-lifecycles/note.md).

---

## Architecture

### 2.1 End-to-end promotion flow (cross-account example: `test` → `beta`)

```
   SENDING ACCOUNT (TEST)                         RECEIVING ACCOUNT (PROD)
   ─────────────────────────                      ──────────────────────────────
   Origin pipeline (template-pipeline*.yml)
     Source → Build → Deploy → [PostDeploy]
                                   │
                        [ApproveToPromote]  (manual, if PromoteApprovalRequired)
                                   │
                              ┌─ Promote (CodeBuild, PromoteServiceRole)
                              │    • zip SourceArtifact → source.zip
                              │    • write promote.json (audit)
                              │    • cross-account PutObject ─────────────┐
                              └───────────────────────────────────────────┼──────────┐
                                                                           ▼          │
                                              s3://<recv-promotion-area>/promotions/   │
                                                <prefix>-<projectId>/<beta>/source.zip │
                                                                           │           │
                                              S3 Object Created event ──▶ EventBridge  │
                                                                           │  rule     │
                                                                           ▼           │
                                              StartPipelineExecution (SourceEvent role)│
                                                                           │           │
                                   Receiving pipeline (template-pipeline-promoted-artifact.yml)
                                     Source(S3) → [ApproveRelease] → Build → [Deploy] → [PostDeploy]
                                                                              │
                                                                    [ApproveToPromote] → [Promote] ──▶ prod
```

Within a single account holding DEV/TEST/PROD, the flow is identical except `PromoteTargetAccountId` is empty (target = current account) and no cross-account bucket policy statement is required.

### 2.2 Component inventory

**Existing templates modified (additive):**
- `template-pipeline.yml` (v2.0.22 → v2.0.23) — CodeCommit origin
- `template-pipeline-github.yml` (v2.0.4 → v2.0.5) — GitHub/CodeConnections origin
- `template-pipeline-build-only.yml` (v2.0.6 → v2.0.7) — build-only origin
- `account/account-wide-infrastructure.yml` (stays v0.0.0) — bucket, bucket policy, EventBridge

**New template:**
- `template-pipeline-promoted-artifact.yml` (v0.0.0) — S3-triggered receiving pipeline

**New modules (`modules/pipeline/`):**
- `promote-project.yml`, `promote-service-role.yml`, `promote-log-group.yml`
- `promotion-source-event-rule.yml`, `promotion-source-event-service-role.yml`

**Modules modified in place (unversioned):**
- `modules/account-wide/s3-artifacts-bucket.yml` — optional EventBridge notifications, `BucketOwnerEnforced` ownership, and noncurrent-version retention change (30 → 365 days, per DD-1 Option 3)
- `modules/account-wide/s3-artifacts-bucket-policy.yml` — optional cross-account statement

**Unchanged (verified adequate):** `modules/management-roles/pipeline-mgmt-role.yml`, `account/prefix-based-infrastructure.yml`.

---

## Components and Interfaces

This section indexes the components introduced or modified by this design and the interfaces (parameters, conditions, IAM, events, keys) that connect them. Detailed specifications follow in the numbered sections referenced below.

### Component summary

| Component | Kind | Change | Detailed section |
|---|---|---|---|
| `template-pipeline*.yml` origin pipelines | Modified templates | additive Promote stage + parameters | §3.1, §4.1 |
| `template-pipeline-promoted-artifact.yml` | New receiving template | S3-triggered pipeline | §3.2, §4.2 |
| `promote-project.yml` | New module (CodeBuild) | archive + manifest writer | §5.1, §8 |
| `promote-service-role.yml` | New module (IAM Role) | sole cross-account writer | §6.1, §8 |
| `promote-log-group.yml` | New module (Log Group) | Promote build logs | §8 |
| `promotion-source-event-rule.yml` | New module (Events Rule) | S3 → pipeline trigger | §7.4, §8 |
| `promotion-source-event-service-role.yml` | New module (IAM Role) | `StartPipelineExecution` | §6.2, §8 |
| `s3-artifacts-bucket.yml` | Modified module | EventBridge + ownership + lifecycle | §7.1–§7.3 |
| `s3-artifacts-bucket-policy.yml` | Modified module | cross-account write statement | §6.3 |

### Interface contracts

- **Parameters and conditions** — the additive, default-off parameter surface and the conditions that gate every new resource/stage are defined in §3.
- **Pipeline stage interface** — inline, conditionally-included stages (`ApproveToPromote`, `Promote`, `ApproveRelease`, S3 `Source`) are defined in §4; fixed action names form the contract consumed by the audit CLI (§4.3, §10).
- **Promote build interface** — the environment-variable contract passed to the inline buildspec is defined in §5.1.
- **IAM interface** — role trust, scoped policies, and the cross-account bucket-policy statement are defined in §6.
- **Event interface** — the S3 `Object Created` event pattern and pipeline target are defined in §7.4.
- **Module authoring contracts** — parent-parameter/condition/sibling-logical-ID contracts for each new module are tabulated in §8.

---

## Data Models

Two data models define the contract between the sending and receiving pipelines.

### Promotion S3 key model

Promotions are addressed by a **stable, derived** key (Option A, Q1) so the trigger key never changes between promotions:

```
promotions/<Prefix>-<ProjectId>/<TargetStageId>/source.zip     # trigger object
promotions/<Prefix>-<ProjectId>/<TargetStageId>/promote.json   # audit manifest
```

- `Prefix` and `ProjectId` are identical across accounts (Assumption 1); the sender's `PromoteTargetStageId` equals the receiver's `StageId` (Req 10.7), so both sides derive the same key without parameterization. See §5.2.
- The commit SHA lives in the manifest and the S3 object version, **not** the key — enabling rollback by re-writing a prior archive as a new version of the same key (§7.4).

### Audit manifest (`promote.json`)

A write-only audit record co-located with the archive. The full JSON schema and field semantics are specified in §5.4. Field summary:

| Field | Meaning |
|---|---|
| `project`, `prefix` | Origin `ProjectId` / `Prefix` |
| `git_sha`, `git_sha_short` | Full 40-char and 7-char commit identifiers |
| `source_archive_key` | Key of the promoted `source.zip` |
| `promoted_from_stage`, `target_stage` | Origin `StageId` and `PromoteTargetStageId` |
| `promoted_at` | ISO-8601 UTC timestamp |
| `source_account_id`, `target_account_id`, `target_region`, `target_bucket` | Resolved routing values |
| `source_pipeline_execution_id` | Originating pipeline execution id |
| `post_deploy_passed` | Whether PostDeploy validation passed before promotion |

`target_deploy_env` and `promoted_by` are intentionally omitted (Req 10.2, 11.5).

---

## 3. Parameters and Conditions

### 3.1 New parameters — origin templates (`template-pipeline*.yml`)

Grouped under a new metadata group **"Promotion (Send to Next Stage)"**, placed immediately after the "Post Deploy Environment Information" group.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `PromoteTargetStageId` | String | `""` | Receiving `StageId`. **Non-empty enables the Promote stage** (and the approval gate unless disabled). Pattern mirrors `StageId` but allows empty: `^$\|^[a-z][a-z0-9-]{0,6}[a-z0-9]$`. |
| `PromoteApprovalRequired` | String | `true` | `true`/`false`. When `true`, insert `ApproveToPromote` before Promote. Description includes the ungated-into-PROD warning (Req 6.3). |
| `PromoteTargetAccountId` | String | `""` | Empty ⇒ same-account. Pattern `^$\|^\d{12}$`. |
| `PromoteTargetRegion` | String | `""` | Empty ⇒ current region. Pattern `^$\|^[a-z]{2}-[a-z]+-\d$`. |
| `PromoteTargetBucket` | String | `""` | Empty ⇒ derive (see §5.3). Pattern `^$\|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$`. |

> The origin templates already define `Prefix`, `ProjectId`, `StageId`, `S3BucketNameOrgPrefix`, `S3ArtifactsBucket`, `RolePath`, `PermissionsBoundaryArn`, `AlarmNotificationEmail`, `DeployEnvironment`, and the notification topic — all reused by the Promote stage/role.

### 3.2 New parameters — receiving template (`template-pipeline-promoted-artifact.yml`)

Includes the full standard parameter set (naming, `DeployEnvironment`, `S3ArtifactsBucket`, `BuildSpec`, PostDeploy group, module source, managed-policy lists, `AlarmNotificationEmail`) **minus** `Repository`/`RepositoryBranch`/`GitHubConnectionArn` (source is S3), **plus:**

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `ReleaseApprovalRequired` | String | `true` | `true`/`false`. When `true`, insert `ApproveRelease` after Source, before Build. Description includes the auto-release warning (Req 6.4). |
| `DeployStageEnabled` | String | `true` | `true`/`false`. When `false`, omit the Deploy stage (build-only-style receiving workload, Req 4.4 / R7b). |
| `PromoteTargetStageId`, `PromoteApprovalRequired`, `PromoteTargetAccountId`, `PromoteTargetRegion`, `PromoteTargetBucket` | — | — | Same as §3.1, for **chained** promotion (`beta → prod`). |

The receiving pipeline's watched key is derived from its **own** `Prefix`/`ProjectId`/`StageId` (§5.2).

### 3.3 New parameters — `account-wide-infrastructure.yml`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `PromotionSourceAccountIds` | CommaDelimitedList | `""` | Accounts allowed to write promotions cross-account. Empty ⇒ statement omitted. |
| `EnableS3ArtifactsBucketEventBridge` | String | `false` | `true`/`false`. Opt-in EventBridge notifications on the account-wide artifacts bucket. |

*(Per DD-1 = Option 3, promotions live in the account-wide artifacts bucket; there is no separate promotions bucket.)*

### 3.4 New conditions

**Origin + receiving templates:**
- `IsPromoteEnabled: !Not [!Equals [!Ref PromoteTargetStageId, ""]]`
- `IsPromoteApprovalRequired: !Equals [!Ref PromoteApprovalRequired, "true"]`
- `IsPromoteEnabledAndApprovalRequired: !And [IsPromoteEnabled, IsPromoteApprovalRequired]`
- `IsPromoteEnabledAndNotDev: !And [IsNotDevelopment, IsPromoteEnabled]`
- `HasPromoteTargetAccount: !Not [!Equals [!Ref PromoteTargetAccountId, ""]]`
- `HasPromoteTargetRegion: !Not [!Equals [!Ref PromoteTargetRegion, ""]]`
- `HasPromoteTargetBucket: !Not [!Equals [!Ref PromoteTargetBucket, ""]]`

**Receiving template additionally:**
- `IsReleaseApprovalRequired: !Equals [!Ref ReleaseApprovalRequired, "true"]`
- `IsDeployStageEnabled: !Equals [!Ref DeployStageEnabled, "true"]`

**account-wide-infrastructure.yml:**
- `HasPromotionSourceAccounts: !Not [!Equals [!Join ["", !Ref PromotionSourceAccountIds], ""]]`
- `EnableArtifactsBucketEventBridge: !Equals [!Ref EnableS3ArtifactsBucketEventBridge, "true"]`

---

## 4. Pipeline stage composition

All new stages are **inline** blocks on `ProjectPipeline`, conditionally included with `Fn::If [<condition>, {stage}, !Ref 'AWS::NoValue']` — matching the existing PostDeploy pattern.

### 4.1 Origin templates — appended stages

Order: `... → [PostDeploy] → [ApproveToPromote] → [Promote]`

**ApproveToPromote** (included when `IsPromoteEnabledAndApprovalRequired`):
```yaml
- !If
  - IsPromoteEnabledAndApprovalRequired
  - Name: ApproveToPromote
    Actions:
      - Name: ApproveToPromote
        ActionTypeId: { Category: Approval, Owner: AWS, Provider: Manual, Version: 1 }
        Configuration:
          NotificationArn: !Ref PipelineNotificationTopic
          CustomData: !Sub "Approve promotion of ${Prefix}-${ProjectId}-${StageId} to stage '${PromoteTargetStageId}'. Review the execution before approving."
          ExternalEntityLink: !Sub "https://${AWS::Region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/${Prefix}-${ProjectId}-${StageId}-Pipeline/view?region=${AWS::Region}"
        RunOrder: 1
  - !Ref 'AWS::NoValue'
```

**Promote** (included when `IsPromoteEnabled`):
```yaml
- !If
  - IsPromoteEnabled
  - Name: Promote
    Actions:
      - Name: Promote
        ActionTypeId: { Category: Build, Owner: AWS, Provider: CodeBuild, Version: 1 }
        Configuration:
          ProjectName: !Sub "${Prefix}-${ProjectId}-${StageId}-Promote"
        InputArtifacts:
          - Name: !Sub "${ProjectId}-${StageId}-SourceArtifact"
        RunOrder: 1
  - !Ref 'AWS::NoValue'
```

The Promote action consumes the **SourceArtifact** (already produced by the Source stage), satisfying "reuse SourceArtifact" (Req 1.2). The pipeline `DependsOn` gains `PromoteProject` via a conditional — handled by making the pipeline depend on `CodeBuildProject` only, and relying on the module's own condition (the Promote project exists whenever `IsPromoteEnabledAndNotDev`).

### 4.2 Receiving template — stage composition

Order: `Source(S3) → [ApproveRelease] → Build → [Deploy] → [PostDeploy] → [ApproveToPromote] → [Promote]`

**Source (S3):**
```yaml
- Name: Source
  Actions:
    - Name: PromotedArtifact
      ActionTypeId: { Category: Source, Owner: AWS, Provider: S3, Version: 1 }
      Configuration:
        S3Bucket: !Ref S3ArtifactsBucket           # account-wide artifacts bucket (DD-1 = Option 3)
        S3ObjectKey: !Sub "promotions/${Prefix}-${ProjectId}/${StageId}/source.zip"
        PollForSourceChanges: "false"
      OutputArtifacts:
        - Name: !Sub "${ProjectId}-${StageId}-SourceArtifact"
      RunOrder: 1
```

**ApproveRelease** (included when `IsReleaseApprovalRequired`): a Manual approval action named `ApproveRelease`, publishing to `PipelineNotificationTopic`, inserted as its own stage between Source and Build.

**Build / Deploy / PostDeploy:** identical to the existing templates. Build reuses the `codebuild-project.yml` module unchanged (same env vars, image, buildspec resolution). Deploy is wrapped in `Fn::If [IsDeployStageEnabled, {deploy stage}, !Ref 'AWS::NoValue']`.

**ApproveToPromote / Promote:** identical to §4.1 (chained promotion).

### 4.3 Detectability for the audit CLI

Approval **action names** are fixed strings — `ApproveToPromote` and `ApproveRelease` — so the audit CLI can detect presence/absence by inspecting `get-pipeline` output (Req 3.8, 5.4, 14).

---

## 5. Promote stage: archive + manifest

### 5.1 `promote-project.yml` (CodeBuild) — inline buildspec

The Promote CodeBuild project uses the same image/compute as Build and a **framework-owned inline buildspec** (Req 9.6). Environment variables (resolved at deploy time):

| Env var | Value |
|---|---|
| `PREFIX`, `PROJECT_ID`, `STAGE_ID` | `Prefix` / `ProjectId` / `StageId` |
| `PROMOTE_TARGET_STAGE_ID` | `PromoteTargetStageId` |
| `PROMOTE_TARGET_BUCKET` | resolved target bucket (§5.3) |
| `PROMOTE_TARGET_REGION` | resolved target region (`PromoteTargetRegion` or `AWS::Region`) |
| `PROMOTE_TARGET_ACCOUNT_ID` | `PromoteTargetAccountId` or `AWS::AccountId` |
| `SOURCE_ACCOUNT_ID`, `AWS_REGION` | `AWS::AccountId` / `AWS::Region` |
| `PROMOTION_KEY_PREFIX` | `promotions/${Prefix}-${ProjectId}/${PromoteTargetStageId}` |

Inline buildspec behavior (executed in the Promote container, with the SourceArtifact mounted at `CODEBUILD_SRC_DIR`):
1. Resolve the commit SHA from `CODEBUILD_RESOLVED_SOURCE_VERSION` (full 40-char; derive 7-char short).
2. Create `source.zip` from the contents of `CODEBUILD_SRC_DIR` (repo tree), so the receiving S3 Source unpacks an identical working tree.
3. `aws s3 cp source.zip s3://$PROMOTE_TARGET_BUCKET/$PROMOTION_KEY_PREFIX/source.zip --region $PROMOTE_TARGET_REGION` (write **last-but-one**).
4. Build `promote.json` (§5.4) and `aws s3 cp promote.json s3://.../promote.json`.
5. Write `source.zip` **last** so the object-created event that triggers the receiving pipeline corresponds to a fully-written archive **and** an already-present manifest. *(Ordering rationale: the trigger is `source.zip`; the manifest must exist before it.)*

> **Note on cross-account object ownership:** if the target bucket is not Bucket-Owner-Enforced, the buildspec adds `--acl bucket-owner-full-control` on upload (Req 7.6). §7.2 covers verification.

### 5.2 Key convention (derived, not parameterized)

- Origin writes to: `promotions/<Prefix>-<ProjectId>/<PromoteTargetStageId>/{source.zip,promote.json}`
- Receiving watches: `promotions/<Prefix>-<ProjectId>/<StageId>/source.zip`
- Because `Prefix`/`ProjectId` are identical across accounts (Assumption 1) and the sender's `PromoteTargetStageId` equals the receiver's `StageId` (Req 10.7), both sides compute the same key.

### 5.3 Target bucket resolution

```
PROMOTE_TARGET_BUCKET =
  HasPromoteTargetBucket ? PromoteTargetBucket
  : UseS3BucketNameOrgPrefix
      ? "${S3BucketNameOrgPrefix}-cf-artifacts-${TargetAccount}-${TargetRegion}-an"
      : "cf-artifacts-${TargetAccount}-${TargetRegion}-an"
where TargetAccount = HasPromoteTargetAccount ? PromoteTargetAccountId : AWS::AccountId
      TargetRegion  = HasPromoteTargetRegion  ? PromoteTargetRegion    : AWS::Region
```
This mirrors the account-wide bucket naming in `s3-artifacts-bucket.yml` (DD-1 = Option 3: promotions live in the account-wide artifacts bucket).

### 5.4 Manifest schema (`promote.json`) — write-only audit

```json
{
  "project": "<ProjectId>",
  "prefix": "<Prefix>",
  "git_sha": "<full 40-char>",
  "git_sha_short": "<7-char>",
  "source_archive_key": "promotions/<prefix>-<projectId>/<targetStage>/source.zip",
  "promoted_from_stage": "<StageId>",
  "target_stage": "<PromoteTargetStageId>",
  "promoted_at": "<ISO-8601 UTC>",
  "source_account_id": "<AWS::AccountId>",
  "target_account_id": "<resolved>",
  "target_region": "<resolved>",
  "target_bucket": "<resolved>",
  "source_pipeline_execution_id": "<CODEBUILD_INITIATOR / pipeline execution id>",
  "post_deploy_passed": true
}
```
`target_deploy_env` is intentionally omitted (Req 10.2). `promoted_by` is omitted (native approvals don't expose approver identity to the build; CodePipeline history is the approver record — Req 11.5).

---

## 6. IAM design

### 6.1 `promote-service-role.yml` (new)

`AWS::IAM::Role`, condition `IsPromoteEnabledAndNotDev`, name `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteServiceRole`, trusted by `codebuild.amazonaws.com`, following the PostDeploy role conventions (path, permissions boundary). Inline policy `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteServicePolicy`:

| Sid | Actions | Resource |
|---|---|---|
| `AllowPromoteToManageItsLogs` | `logs:*` | `arn:aws:logs:<region>:<acct>:log-group:/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Promote:*` |
| `ReadSourceArtifact` | `s3:GetObject`, `s3:GetObjectVersion`, `s3:ListBucket` | local `${S3ArtifactsBucket}` + `/*` (to read the input SourceArtifact) |
| `WritePromotionToTarget` | `s3:PutObject`, `s3:PutObjectAcl` (only if ownership not enforced), `s3:GetObject`, `s3:GetObjectVersion` | `arn:aws:s3:::<PromoteTargetBucket>/promotions/*` |

The `WritePromotionToTarget` resource uses the **resolved target bucket** ARN. Because the target bucket ARN is region-agnostic, the same statement works same- and cross-region.

> **Least privilege:** write is limited to the `promotions/*` prefix; the role cannot touch other keys in the target bucket. Only this role — not `CodeBuildServiceRole`/`PostDeployServiceRole` — carries cross-account write (Req 9.3).

### 6.2 `promotion-source-event-service-role.yml` (new)

Mirrors `source-event-service-role.yml`: `AWS::IAM::Role` trusted by `events.amazonaws.com`, condition `IsNotDevelopment`, name `${Prefix}-Worker-${ProjectId}-${StageId}-PromotionSourceEventServiceRole`, single statement allowing `codepipeline:StartPipelineExecution` on `arn:aws:codepipeline:<region>:<acct>:${Prefix}-${ProjectId}-${StageId}-Pipeline`. Used by the receiving template only.

### 6.3 Cross-account bucket policy statement (`s3-artifacts-bucket-policy.yml`)

Appended, wrapped in `Fn::If [HasPromotionSourceAccounts, {statement}, !Ref 'AWS::NoValue']`:

```yaml
- Sid: "AllowCrossAccountPromotionWrite"
  Effect: Allow
  Principal:
    AWS: !Ref PromotionSourceAccountIds        # list of account roots
  Action:
    - s3:PutObject
    - s3:GetObject
    - s3:GetObjectVersion
  Resource:
    - Fn::Sub: "${S3ArtifactsBucketRegional.Arn}/promotions/*"
  Condition:
    StringLike:
      "aws:PrincipalArn": "arn:aws:iam::*:role/*-PromoteServiceRole"
```

Design notes:
- `Principal.AWS` accepts the account-ID list natively → **no list iteration** (R2).
- The single `StringLike` on `aws:PrincipalArn` constrains the role name across all listed accounts and spans any `RolePath` (the `*` matches `/path/segments/`). Scoping to accounts is handled by `Principal`; scoping to the role is handled by the condition (Req 7.3, 7.5).
- Resource restricted to `.../promotions/*` (Req 7.4).
- The existing `DenyNonSecureTransportAccess` statement continues to apply (TLS enforced).

### 6.4 Management role adequacy (no change) — verification

`pipeline-mgmt-role.yml` already grants (prefix-scoped) `codebuild:*`, `events:*`, `codepipeline:*`, `sns:*`, `logs:*`, and `iam:*` on `${Prefix}-Worker-*`. Creating the Promote project, PromoteServiceRole, PromotionSourceEventServiceRole, event rule, and inline approval actions falls within these. A worker role whose inline policy *references* a cross-account bucket ARN is still created via `iam:CreateRole`/`iam:PutRolePolicy` on `${Prefix}-Worker-*` — no new management permission (Req 16.1, 16.3). **Design action:** confirm by reading `pipeline-mgmt-role.yml` during implementation task 0 and record the finding; if a gap is found, raise before proceeding (do not silently widen the role).

---

## 7. Account-wide bucket changes

### 7.1 EventBridge enablement (`s3-artifacts-bucket.yml`)

Add an opt-in notification configuration:
```yaml
NotificationConfiguration:
  Fn::If:
    - EnableArtifactsBucketEventBridge
    - EventBridgeConfiguration: {}
    - Ref: "AWS::NoValue"
```
Default (`false`) leaves existing deployments unchanged (Req 8.1). When enabled, the account-wide artifacts bucket emits `Object Created` events to the default event bus in the bucket's region; the receiving-region rule (§7.4) consumes them — this is what makes cross-region promotion work with no extra components (NFR #4).

### 7.2 Object ownership verification

`s3-artifacts-bucket.yml` does not currently set `OwnershipControls`. **Design action:** add `OwnershipControls: Rules: [{ ObjectOwnership: BucketOwnerEnforced }]` (ACLs disabled) so cross-account-written objects are automatically owned by the receiving account, and the Promote upload needs **no** ACL. This is additive and safe (the bucket already blocks public access). If BucketOwnerEnforced is undesirable for other reasons, the fallback is the `--acl bucket-owner-full-control` path in §5.1 (Req 7.6).

### 7.3 DD-1 — Promotions retention (RESOLVED: Option 3)

**Constraint (confirmed via AWS docs):** the account-wide bucket's existing lifecycle rule (`ExpireObjects`) uses an empty filter (all objects) with `ExpirationInDays: 395` and `NoncurrentVersionExpirationInDays: 30`. S3 resolves overlapping rules by applying the **shorter** action ([lifecycle-conflicts.html](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-conflicts.html), Examples 2–4), and offers no "exclude prefix/tag" filter. Therefore an added `promotions/*` rule **cannot** extend retention beyond the whole-bucket rule.

**Decision: Option 3 (single bucket, relax the whole-bucket rule).** Promotions remain in the account-wide artifacts bucket (preserving R3a — one bucket for both S3 Source and ArtifactStore). The `ExpireObjects` rule is modified as follows:

```yaml
LifecycleConfiguration:
  Rules:
    - Id: "ExpireObjects"
      AbortIncompleteMultipartUpload:
        DaysAfterInitiation: 1
      ExpirationInDays: 395                      # UNCHANGED (current version)
      NoncurrentVersionExpirationInDays: 365     # CHANGED: 30 -> 365 (rollback window)
      Status: "Enabled"
```

Effects and accepted tradeoffs:
- **Rollback window:** promoted archives (and all other objects) retain noncurrent versions for **365 days** — satisfies the 365-day rollback intent (Req 12.1).
- **Current promotion objects still expire at 395 days:** the "current never expires" intent (Req 12.2) is **documented but not honored**. Impact is limited to a stage not promoted-to for 395 days losing its `source.zip` pointer, which the next promotion re-creates.
- **Cost tradeoff:** noncurrent versions of *all* artifacts (not just promotions) are now kept 365 days. Ordinary artifacts are mostly unique keys, so noncurrent accumulation is expected to be modest; accepted for this release.
- **No separate `promotions/*` rule** is added (it cannot help — see constraint).

The limitation and future alternatives (dedicated promotions bucket, tag-based split, revisiting the bucket-wide bump) are recorded in [`.kiro/specs/future-s3-artifact-lifecycles/note.md`](../future-s3-artifact-lifecycles/note.md). Since `account-wide-infrastructure.yml` is in development mode (v0.0.0), no version bump is required for this change.

### 7.4 `promotion-source-event-rule.yml` (new, receiving template)

`AWS::Events::Rule`, condition `IsNotDevelopment`, name `${Prefix}-${ProjectId}-${StageId}-PromotionSourceEvent`:
```yaml
EventPattern:
  source: ["aws.s3"]
  detail-type: ["Object Created"]
  detail:
    bucket:
      name: [ <account-wide artifacts bucket name = S3ArtifactsBucket> ]
    object:
      key: [ "promotions/${Prefix}-${ProjectId}/${StageId}/source.zip" ]
Targets:
  - Arn: arn:aws:codepipeline:<region>:<acct>:${Prefix}-${ProjectId}-${StageId}-Pipeline
    Id: PromotedArtifactPipelineTarget
    RoleArn: <PromotionSourceEventServiceRole.Arn>
```
Watching the exact `source.zip` key means the rule fires only on a completed promotion write (the manifest is written earlier per §5.1). Re-writing a prior archive (rollback) creates a new version of the same key → new `Object Created` event → pipeline re-triggers (Req 1.5, 8.4).

---

## 8. Module contracts (authoring)

Each new module opens with a contract comment block (parent parameters, conditions, sibling logical IDs) and uses **long-form intrinsics only**, per module standards.

| Module | Type | Condition | Key parent contract |
|---|---|---|---|
| `promote-project.yml` | `AWS::CodeBuild::Project` | `IsPromoteEnabledAndNotDev` | params: Prefix/ProjectId/StageId, PromoteTarget*, S3ArtifactsBucket, S3BucketNameOrgPrefix; sibling role `PromoteServiceRole`; conditions `UseS3BucketNameOrgPrefix`, `HasPromoteTarget*` |
| `promote-service-role.yml` | `AWS::IAM::Role` | `IsPromoteEnabledAndNotDev` | params: Prefix/ProjectId/StageId, RolePath, PermissionsBoundaryArn, S3ArtifactsBucket, PromoteTargetBucket + resolution conditions; conditions `HasPermissionsBoundaryArn` |
| `promote-log-group.yml` | `AWS::Logs::LogGroup` | `IsPromoteEnabledAndNotDev` | params: Prefix/ProjectId/StageId; name `/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Promote`, retention 90 |
| `promotion-source-event-rule.yml` | `AWS::Events::Rule` | `IsNotDevelopment` | params: Prefix/ProjectId/StageId, promotion bucket; sibling role `PromotionSourceEventServiceRole` |
| `promotion-source-event-service-role.yml` | `AWS::IAM::Role` | `IsNotDevelopment` | params: Prefix/ProjectId/StageId, RolePath, PermissionsBoundaryArn; conditions `HasPermissionsBoundaryArn` |

Parent templates consuming these declare all listed parameters/conditions, use the exact sibling logical IDs (`PromoteServiceRole`, `PromotionSourceEventServiceRole`), and add cfn-lint suppressions (`E6101`, `W2001`, `W8001`) already present in the pipeline templates.

---

## 9. Notifications (Req 13)

Both approval actions set `NotificationArn: !Ref PipelineNotificationTopic` (the existing SNS topic with the `AlarmNotificationEmail` subscription) — no new topic (Req 13.1). CodePipeline's native approval notification includes the pipeline/stage/action and an approval-review link; `CustomData` adds project/prefix/stage/target-stage context and `ExternalEntityLink` provides the execution console URL (Req 13.2, 13.3). On rejection the pipeline stops and the Promote stage never runs, so no archive/manifest is written (Req 13.4).

> The commit SHA in the approval message is best-effort: native approval `CustomData` is static (set at deploy time), so it references the stage/target rather than the runtime SHA. The runtime SHA is always recorded in the manifest and CodePipeline source-revision metadata. **Design note:** if surfacing the live SHA in the approval message is required, it would need a small notifier (out of current scope) — flagged, not assumed.

---

## 10. Admin-ops approval-audit CLI (Req 14)

Documented in `docs/admin-ops/` as three copy-paste one-liners using detection method A (structure inspection), scoped to Atlantis pipelines via the `Atlantis=pipeline-infrastructure` tag.

Approach (documented, not a committed script):
1. Enumerate Atlantis pipelines by tag using the Resource Groups Tagging API:
   `aws resourcegroupstaggingapi get-resources --resource-type-filters codepipeline --tag-filters Key=Atlantis,Values=pipeline-infrastructure`
2. For each, `aws codepipeline get-pipeline --name <n>` and inspect stage/action names with `jq`:
   - **Command 1 (promote gate off):** has a stage named `Promote` but no action named `ApproveToPromote`.
   - **Command 2 (release gate off):** has an S3 source (promoted-artifact pipeline) but no action named `ApproveRelease` before `Build`.
   - **Command 3 (either):** union of the above.

**Design action (Req 14.6):** confirm the `Atlantis=pipeline-infrastructure` tag is present on deployed pipelines and queryable via the tagging API / `list-tags-for-resource`. The tag is applied at deploy time (stack tags propagate to the pipeline); the exact one-liners will be finalized against real output during implementation.

---

## 11. Versioning, changelog, documentation (Reqs 17, 18)

- **First edit to each template** bumps the header version + date: `template-pipeline.yml` → v2.0.23, `-github.yml` → v2.0.5, `-build-only.yml` → v2.0.7. New `template-pipeline-promoted-artifact.yml` starts at v0.0.0. `account-wide-infrastructure.yml` stays v0.0.0 (dev mode).
- No breaking changes; no new versioned `-v2-1.yml` files.
- Add `## v0.0.40 - unreleased` to `CHANGELOG.md` (append only), with per-template entries referencing this spec.
- Docs: new `docs/templates/v2/pipeline/template-pipeline-promoted-artifact-README.md`; update the three existing pipeline READMEs (preserve blockquotes/custom content) and the pipeline category README; approval-audit CLI in `docs/admin-ops/`; manual two-account integration test in `docs/maintainer/`.

---

## Correctness Properties

The design is expected to preserve the following invariants; the testing strategy (§12) validates them:

1. **Backward compatibility (default-off).** With all promotion parameters at their defaults, every modified template renders structurally identical to its prior version — no `Promote`, `ApproveToPromote`, `ApproveRelease`, or cross-account statement appears (Req 3.7, NFR #1).
2. **Approval-gate presence.** `PromoteApprovalRequired=true` ⟺ `ApproveToPromote` precedes `Promote`; `ReleaseApprovalRequired=true` ⟺ `ApproveRelease` sits between Source and Build. The two gates are independent (R5, T1).
3. **Key agreement.** For matching `Prefix`/`ProjectId` and sender `PromoteTargetStageId` = receiver `StageId`, the sender's write key equals the receiver's watched key (§5.2).
4. **Write ordering.** `promote.json` is written before `source.zip`; the trigger fires only on the fully-written `source.zip`, guaranteeing the manifest is present when the receiving pipeline starts (§5.1, §7.4).
5. **Least privilege.** Cross-account write is confined to a single role pattern (`*-PromoteServiceRole`), a single prefix (`promotions/*`), and an explicit account list (`PromotionSourceAccountIds`), over TLS only; no AWS managed full-access policies are used (§6).
6. **Idempotent re-trigger.** Re-writing a prior archive (rollback) produces a new object version of the same key and a new `Object Created` event, re-triggering the receiving pipeline (Req 1.5, 8.4).
7. **Auditability.** Approval action names are fixed strings, so the presence/absence of each gate is detectable from `get-pipeline` output (§4.3, §10).

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Approval rejected (`ApproveToPromote` or `ApproveRelease`) | Pipeline stops at the gate; the Promote stage never runs, so no archive/manifest is written (Req 13.4). |
| Promote build fails before upload | CodeBuild action fails; no partial `source.zip` is written; the origin pipeline execution is marked failed and surfaced via existing pipeline alarms/notifications. |
| Cross-account `PutObject` denied | Promote build fails with an S3 AccessDenied error; the receiving pipeline is not triggered. Resolution: confirm `PromotionSourceAccountIds` includes the sender and the writer matches `*-PromoteServiceRole` (§6.3). |
| Object ownership mismatch (ACLs enabled on target) | Mitigated by `BucketOwnerEnforced` on the target bucket (§7.2); fallback path adds `--acl bucket-owner-full-control` on upload (§5.1). |
| Manifest present but `source.zip` write fails | The trigger object (`source.zip`) never appears, so the receiving pipeline does not start; the stale manifest is harmless and is overwritten on the next attempt. |
| EventBridge not enabled on target bucket | No trigger fires. Resolution: deploy account-wide infrastructure with `EnableS3ArtifactsBucketEventBridge=true` (§7.1). |
| Current promotion object expires at 395 days (DD-1 limitation) | Receiving stage loses its `source.zip` pointer until the next promotion re-creates it; noncurrent versions are still retained 365 days for rollback (§7.3). |

---

## Testing Strategy

- **cfn-lint** on every changed/added template and (via a consuming test harness) the new modules. Because `AWS::Include` bodies are invisible to cfn-lint, module correctness is validated by linting the parent templates that consume them plus targeted YAML/structure checks.
- **Unit-style checks** (fast, concrete) over property-based tests, per testing guidelines. Examples:
  - Promotion parameters absent/default ⇒ rendered origin pipeline has no `Promote`/`ApproveToPromote` stage (backward-compat, Req 3.7).
  - `PromoteTargetStageId` set + `PromoteApprovalRequired=true` ⇒ both `ApproveToPromote` and `Promote` present, in order.
  - `PromoteApprovalRequired=false` ⇒ `Promote` present, `ApproveToPromote` absent.
  - Receiving template with `ReleaseApprovalRequired=false` ⇒ no `ApproveRelease`; `DeployStageEnabled=false` ⇒ no Deploy stage.
  - Bucket policy: empty `PromotionSourceAccountIds` ⇒ no cross-account statement; non-empty ⇒ statement present, `promotions/*` only, `*-PromoteServiceRole` condition.
  - Target-bucket derivation matches expected name for org-prefix / no-org-prefix and same/cross account/region.
- **Suite target:** < 30 seconds total; clean up temp render files.
- **Cross-account behavior** is validated by a **documented manual two-account procedure** in `docs/maintainer/` (not CI).

---

## 13. Backward compatibility & security summary

- **Backward compatible:** all origin-template changes are additive and gated on `IsPromoteEnabled`/approval conditions; `account-wide-infrastructure.yml` changes are gated on the new default-off parameters. With defaults, rendered templates are structurally unchanged (Req NFR #1).
- **Least privilege:** cross-account write is a single role pattern (`*-PromoteServiceRole`), a single prefix (`promotions/*`), specific accounts (`PromotionSourceAccountIds`), TLS-enforced. No AWS managed full-access policies.
- **Security callout:** the `PromoteApprovalRequired`/`ReleaseApprovalRequired` defaults are `true`; disabling both is the only path to fully ungated promotion, is prominently warned in the parameter descriptions, and is auditable via the admin-ops CLI.

---

## 14. Open items for reviewer

1. ~~**DD-1 (§7.3):** promotions retention.~~ **RESOLVED — Option 3** (relax whole-bucket noncurrent to 365 days; keep 395-day current expiry; limitation recorded in [`.kiro/specs/future-s3-artifact-lifecycles/note.md`](../future-s3-artifact-lifecycles/note.md)).
2. **§7.2:** confirm adding `BucketOwnerEnforced` ownership to the account-wide bucket is acceptable.
3. **§9 note:** confirm the execution-link approval message (without live SHA) is sufficient (consistent with Req 13.3), or whether a SHA-in-message notifier should be added later.
