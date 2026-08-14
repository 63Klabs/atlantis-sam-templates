# Cross-Account Serverless CI/CD Promotion
## Pre-Requirements: Recommendations & Clarifying Questions

**Status:** Draft for Developer/Architect Review
**Purpose:** Resolve architectural decisions and open questions before writing `requirements.md`
**Companion Document:** [PRELIMINARY.md](./PRELIMINARY.md)
**Date:** 2026-08-13

---

## 0. How to Use This Document

This document captures what I learned from reviewing the existing repository against `PRELIMINARY.md`, states the recommendations I would carry into `requirements.md`, and lists the decisions I still need from you. Each open item is numbered `Q#` so we can track answers inline (add an **Answer:** line under each, the same way `PRELIMINARY.md` §15 was answered).

Please focus first on the items marked **[BLOCKER]** — those change the shape of the whole design and I cannot write coherent requirements without them.

---

## 1. What I Confirmed About the Existing Codebase

These findings ground the recommendations below. Correct me anywhere I misread the intent.

1. **Pipelines are plain CloudFormation, not SAM.** All three pipeline templates (`template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`) declare a single inline `AWS::CodePipeline::Pipeline` resource named `ProjectPipeline`. Only the supporting resources (roles, CodeBuild projects, log groups, event rules, SNS notification set) are pulled in as modules via `Fn::Transform: AWS::Include`. The pipeline **stages themselves are written inline**, not as modules. **Answer:** Correct
2. **Stage insertion already has a pattern.** The optional PostDeploy stage is inserted with `!If [IsPostDeployEnabled, {stage...}, !Ref 'AWS::NoValue']`. New Approval/Promote stages can follow the exact same conditional-inclusion pattern.
3. **No manual approval exists anywhere today.** There are no `Provider: Manual` actions. This feature introduces the first ones. **Answer:** Correct
4. **No S3 source trigger exists.** `source-event-rule.yml` is CodeCommit-only (EventBridge on `aws.codecommit`). GitHub uses CodeConnections. An S3-object-arrival trigger is entirely new. **Answer:** Correct
5. **`StageId` and `DeployEnvironment` are decoupled and only `DEV` is hard-coded.** The single environment conditional is `IsNotDevelopment: !Not [!Equals [!Ref DeployEnvironment, "DEV"]]`. There is **no** `StageId → DeployEnvironment` mapping table. `"TEST"` / `"PROD"` literals do not appear in conditionals. This is good news for §13 (parameterized stages).  **Answer:** Correct
6. **Naming convention** is `${Prefix}-${ProjectId}-${StageId}-<ResourceId>`; worker IAM roles use a `-Worker-` infix (e.g. `${Prefix}-Worker-${ProjectId}-${StageId}-CodePipelineServiceRole`). Pipeline artifacts drop the Prefix (`${ProjectId}-${StageId}-SourceArtifact`). **Answer:** Correct but I am concerned that the Pipeline artifact drops the prefix. Does this pose an issue as we promote? If it is okay and doesn't break anything if we fix this we should use `${Prefix}-${ProjectId}-${StageId}-SourceArtifact`
7. **Artifact buckets use SSE-S3 (AES256), not KMS.** This materially simplifies cross-account access (no KMS key-policy sharing needed). **Answer:** Correct
8. **The account-wide artifacts bucket is the natural promotion bucket.** `modules/account-wide/s3-artifacts-bucket.yml` + `-bucket-policy.yml` create a shared, account-regional bucket (`[org-]cf-artifacts-<acct>-<region>-an`) whose policy today only grants same-account `*-CodePipelineServiceRole` / `*-CodeBuildServiceRole` / `*-CloudFormationSvcRole`. Lifecycle: 395-day expiration, 30-day noncurrent version expiration. **Answer:** Correct
9. **Deployment permissions come from `prefix-based-infrastructure.yml`** via the `pipeline-mgmt-role.yml` module (the CloudFormation service role that deploys pipeline stacks). It is account- and prefix-scoped (`${Prefix}-*`) and already grants `events:*`, `codebuild:*`, `codepipeline:*`, `sns:*`, and worker-role `iam:*` on `${Prefix}-Worker-*`. **Answer:** Correct

### Current versions (for the version-control plan)

| Template | Current version | Mode |
|---|---|---|
| `template-pipeline.yml` | v2.0.22 | Production (PATCH > 0) — breaking changes need a new file |
| `template-pipeline-github.yml` | v2.0.4 | Production (PATCH > 0) |
| `template-pipeline-build-only.yml` | v2.0.6 | Production (PATCH > 0) |
| `account/prefix-based-infrastructure.yml` | v0.0.2 | Production (PATCH > 0) |
| `account/account-wide-infrastructure.yml` | v0.0.0 | Development (PATCH = 0) |
| pipeline / account-wide modules | unversioned | n/a |
| `CHANGELOG.md` latest | v0.0.39 (**released** 2026-08-11) | — |

> **Note:** The latest CHANGELOG version (v0.0.39) is already dated/released, so per the changelog + spec-naming rules a new `## v0.0.40 - unreleased` header must be added. The spec directory (`0-0-40-...`) already matches that upcoming version, so no rename is needed.

---

## 2. The Central Architectural Question (read first)

**[BLOCKER] Q1 — How does the manifest actually trigger the downstream pipeline, and what is the pipeline's Source artifact?**

This is the crux of the whole feature and the preliminary doc is ambiguous here. CodePipeline is **statically configured** — a Source action watches **one** S3 object key and emits **that object** as the source artifact. It cannot "read a manifest at runtime to decide what to build" the way §5.3 implies. Runtime values like `StageId` / `DeployEnvironment` are fixed when the promotion pipeline stack is deployed (CFN parameters), **not** read from the manifest.

That leaves us with a design choice. My analysis of the options:

- **Option A — Stable trigger key, manifest is audit-only (recommended).**
  The Promote stage writes `source.zip` to a **stable, per-target key** the downstream pipeline watches, e.g. `s3://<receiving-artifacts-bucket>/promotions/<prefix>-<projectId>/<targetStageId>/source.zip`. Because the bucket is versioned, overwriting that key fires an S3/EventBridge event that starts the pipeline, whose S3 Source action emits `source.zip` as the SourceArtifact. The **build then behaves identically to a normal build** (source artifact = full repo at the promoted SHA). The manifest JSON is written alongside purely for audit and is **not** the trigger and **not** the source.
  - *Rollback:* re-write a prior SHA's archive to the stable key (a small "re-promote" action), which re-triggers.
  - *Pro:* build stage is byte-for-byte the existing behavior; no custom "download source.zip" logic. *Con:* the SHA is not in the object key, so per-SHA retention/history relies on bucket versioning + the manifest.

- **Option B — Manifest is the trigger AND the source artifact.**
  The pipeline watches the manifest key; the Build stage reads the manifest, then downloads the SHA-pinned `source.zip` itself before building. Matches §5.3 literally.
  - *Pro:* honors SHA-keyed archive reuse directly. *Con:* the Build stage is **no longer identical** to the existing build (it gains a manifest-parse + fetch-and-unpack preamble), which conflicts with §6.2.2 / §3 goal #2 ("preserving all existing build behaviors") and §6 goal to avoid refactoring buildspecs.

- **Option C — Decoupled trigger via Lambda.**
  S3 event on manifest → EventBridge → small Lambda → `StartPipelineExecution` with a source revision override pointing at the SHA-pinned `source.zip`.
  - *Pro:* keeps SHA-keyed archives and identical build. *Con:* adds a Lambda (new runtime component, more IAM, more to maintain) — heavier than the rest of the framework, which is pure CFN + CodeBuild today.

**My recommendation: Option A.** It satisfies "promote the commit," "identical build behavior," and "trivial rollback" with the least new machinery, and it reuses the existing account-wide artifacts bucket + EventBridge patterns already in the repo. The manifest still provides the full audit record §10 requires.

- **Q1a:** Do you accept Option A, or do you require the literal SHA-keyed-archive-as-source behavior (Option B/C)? **Answer:** Use Option A
- **Q1b:** If Option A: is bucket **versioning** (already enabled) an acceptable mechanism for per-SHA history/rollback, given the 395-day lifecycle window? Or do we also need to keep the immutable per-SHA copy (`.../<sha>/source.zip`) in addition to the stable trigger key? **Answer:** Bucket versioning is acceptable. we do not need to keep the immutable per-SHA copy

---

## 3. Trigger & Source Mechanics

**[BLOCKER] Q2 — S3 event detection method.**
CodePipeline S3 sources detect changes via **EventBridge** (recommended, requires an `AWS::Events::Rule` and, for S3, either EventBridge notifications enabled on the bucket or a CloudTrail data event). The account-wide artifacts bucket does **not** currently enable EventBridge notifications.
- **Recommendation:** Add an optional `EventBridgeConfiguration` (or notification config) to the account-wide artifacts bucket module, gated behind a new opt-in parameter so existing deployments are unaffected. Trigger via a new `modules/pipeline/promotion-source-event-rule.yml` + service role, mirroring the existing `source-event-rule.yml`/`source-event-service-role.yml` pair.
- **Q2a:** OK to enable EventBridge notifications on the account-wide artifacts bucket (opt-in), rather than per-object S3 notification configurations or CloudTrail? **Answer:** Yes, enable EventBridge on the account-wide artifacts.

**Q3 — Trigger key / object-key convention.**
For Option A I propose the watched key:
```
promotions/<prefix>-<projectId>/<targetStageId>/source.zip
promotions/<prefix>-<projectId>/<targetStageId>/promote.json   (manifest, audit)
```
Both the sending pipeline and receiving pipeline can compute this from their own parameters (target stage on the sender, own stage on the receiver).
- **Q3a:** Does this key convention work for you, and should it include the `S3BucketNameOrgPrefix` / region anywhere, or is the bucket name itself sufficient scoping? **Answer:** The bucket name is sufficient for scoping
- **Q3b:** The preliminary example used the reverse (`{prefix}-{project}/{sha}/...`). Confirm we're moving the SHA out of the trigger key (per Q1) and into the manifest + object version. **Answer:** Yes we are moving sha out of the trigger key

**Q4 — Same Prefix/ProjectId across accounts?**
Promotion assumes the receiving pipeline is `${Prefix}-${ProjectId}-${TargetStageId}-Pipeline` and that the key convention is derivable on both sides. This requires **`Prefix` and `ProjectId` to be identical in the sending and receiving accounts** (only `StageId`/account differ).
- **Q4a:** Confirm Prefix + ProjectId are always identical across the promotion path. If not, we need explicit target-naming parameters on the sender. **Answer:** Yes they are always identical across accounts

---

## 4. Commit SHA Handling ("commit sha hashing")

**Q5 — What does "SHA hashing" mean here, concretely?**
My reading: we simply capture the resolved source commit ID rather than compute a new hash. In CodeBuild the resolved commit is available as `CODEBUILD_RESOLVED_SOURCE_VERSION`; CodePipeline also exposes source revision metadata.
- **Recommendation:** Use the resolved commit SHA as the promotion identifier. Store the **full 40-char SHA** in the manifest and object metadata for uniqueness; display the **short 7-char** form in notifications.
- **Q5a:** Is "resolved source commit SHA" the correct interpretation, or did you intend an independently computed content hash of the archive (e.g. to dedupe identical trees across commits)? **Answer:** Commit sha is sufficient
- **Q5b:** For the GitHub pipeline, the CodeConnections source revision is likewise a commit SHA — treat identically? **Answer:** Yes, treat identically

**Q6 — How is `source.zip` produced in the Promote stage?**
The CodePipeline **SourceArtifact is already a zip of the repo at the built commit**. The Promote CodeBuild action receives it as an input artifact, so it can simply re-upload that artifact to the cross-account bucket without re-cloning.
- **Recommendation:** Reuse the existing SourceArtifact as the promotion `source.zip` (no `git archive`, no `codecommit:GitPull`). This also sidesteps the confusing §8.1 line about "`s3:GetObject` on the source CodeCommit repository."
- **Q6a:** Acceptable to promote the pipeline's SourceArtifact directly? (If you specifically need a clean `git archive` — e.g. to exclude CI artifacts or include submodules — say so, as that changes the Promote stage's permissions and logic.) **Answer:** Yes, reuse the existing SourceArtifact

**Q7 — Where does the Promote logic (buildspec) live?**
Existing app buildspecs live in the app repo. Promotion is framework-level plumbing that should not require every app team to add a buildspec.
- **Recommendation:** Provide the promote logic as an **inline `BuildSpec` string** inside the Promote CodeBuild project module (so nothing is required in the app repo). App-repo override optional but not required.
- **Q7a:** Agree with inline framework-owned buildspec for Promote (and for the receiving-side "release" if any)? Or must it be overridable per project like the other buildspecs? **Answer:** I agree with inline and we do not want to provide an app-repo override

---

## 5. Stages, Approvals & the "Versatile / same-account" Model

**Q8 — Confirm the full stage inventory per pipeline role.**
Combining §6, §7, and §12, I read the model as **two independent, optional approval gates plus an optional promote**:

| Pipeline (role) | Source | Build | Deploy | PostDeploy | Approve-to-Promote (sending gate) | Promote | Approve-Release (receiving gate) |
|---|---|---|---|---|---|---|---|
| Origin (`test`/`dev`, existing templates) | ✓ | ✓ | ✓/– | opt | **opt (new)** | **opt (new)** | – |
| Promoted-artifact (new template, e.g. `beta`) | S3 | ✓ | ✓ | opt | **opt (new)** | **opt (new)** | **opt (new)** |
| Promoted-artifact (new template, `prod`) | S3 | ✓ | ✓ | opt | – | – | **opt (new)** |

- **Q8a:** Is that the correct matrix? Specifically, are **both** the "Approve-to-Promote" gate (§7, before Promote) and the "Approve-Release" gate (§12, after Source, before Build) present and **independently toggleable** on the new template? **Answer:** Yes, both are available and independently toggleable. 
- **Q8b:** For the origin templates, the Promote/Approve stages come **after** Deploy/PostDeploy. Confirm ordering: `... → PostDeploy → Approve-to-Promote → Promote`. **Answer:** Yes, that is the correct order

**Q9 — Does `template-pipeline-build-only.yml` participate?**
§6.1 lists all three existing templates, but build-only has **no Deploy/PostDeploy stage** — there is nothing validated to gate on. Promoting an unbuilt/undeployed commit is unusual.
- **Recommendation:** Add Promote/Approve only to `template-pipeline.yml` and `template-pipeline-github.yml`; **exclude** build-only (or treat "promote after build" as a distinct, explicitly-requested case).
- **Q9a:** Exclude build-only, or is there a real use case for promoting straight after a build with no deploy? **Answer:** Yes there is a use case as the Build Only is for CDK, Python Scripts, and CLI commands (copy to S3) which may not need a deploy stage (since there is no deploy, any Post Deploy can take place in the same CodeBuild container). Include build-only pipeline

**Q10 — Approval notifications.**
§7 wants project/prefix/stage/SHA/execution-id/link in the approval notice; §Q3(answered) chose CodePipeline native email. CodePipeline Manual Approval actions publish to an **SNS topic**, and the repo already has `PipelineNotificationTopic` + email subscription.
- **Recommendation:** Reuse the existing `PipelineNotificationTopic` for approval notifications (single email list per pipeline). The approval action's custom message can carry the required fields; the SHA comes from the source revision.
- **Q10a:** Reuse the existing notification topic/email, or do approvers need a **separate** SNS topic / distinct email list from the build-failure notifications? **Answer:** Reuse existing notification email
- **Q10b:** CodePipeline native approvals don't natively deep-link to a specific commit diff; a console link to the execution is the standard. Is the execution link sufficient, or do you want a constructed CodeCommit/GitHub compare URL in the message? **Answer:** Execution link is sufficient.

**Q11 — Same-account ("versatile", §13) differences.**
For a single account holding DEV/TEST/PROD, the mechanism is identical except no cross-account principals are needed.
- **Recommendation:** Drive cross-account behavior purely from parameters (target account ID; when target account == current account, skip cross-account grants). No separate template.
- **Q11a:** Confirm one template covers both cross-account and same-account by parameterization (no `-cross-account` vs `-same-account` variants). **Answer:** Yes, one template covers both (you could even have it if there is no target account provided as a parameter, keep it in the same account)

---

## 6. S3 Bucket & Cross-Account Policy (§8, §11)

**Q12 — Per-account model & the receiving bucket policy.**
Per your §15 answers, the receiving account owns the promotion bucket (its account-wide artifacts bucket), and the sender writes cross-account into it.
- **Recommendation:** Add an **optional** parameter to `account-wide-infrastructure.yml` / the `s3-artifacts-bucket-policy.yml` module, e.g. `PromotionSourceAccountId` (or a list), that appends a policy statement allowing that account's `*-CodeBuildServiceRole` (or `*-CodePipelineServiceRole`) to `s3:PutObject` (and read-back) **only under the `promotions/*` prefix**. Default empty = no cross-account access = fully backward compatible.
- **Q12a:** Scope the grant to a **specific role ARN pattern** in the sending account (`arn:aws:iam::<sendAcct>:role<RolePath>*-CodeBuildServiceRole`), or to the sending **account root** (simpler, broader)? I recommend the role-pattern scoping. **Answer** Scope to the role pattern. I think this receives it's own Service Role though, doesn't CodeBuildServiceRole and PostDeployServiceRole get their own? I don't want the codebuild stages to submit artifacts, only the promote stage. 
- **Q12b:** Restrict the cross-account write to the `promotions/*` key prefix (recommended), or the whole bucket? **Answer:** Yes, restrict to promotions/*
- **Q12c:** Single sending account per bucket (§Q1-answered "per-account") or should the parameter accept a **list** of source accounts? **Answer:** I would prefer a list **but** is there a consistent way to iterate over a list in an IAM policy definition in CloudFormation? I've had issues in the past. Otherwise a single account is fine.
- **Q12d:** Should the sender also need cross-account **read** (e.g. to check for an existing archive), or is write-only sufficient? **Answer:** Read should be allowed as long as it is scoped.

**Q13 — Retention / rollback window.**
§Q2(answered) reuses the existing lifecycle (395-day object expiration, 30-day noncurrent). Under Option A, rollback depends on **noncurrent versions** of the stable key — currently expired after **30 days**.
- **[Potential conflict] Q13a:** A 30-day noncurrent-version expiry gives only a ~30-day rollback window for prior SHAs via versioning. Is that acceptable, or should the promotion prefix have a **longer noncurrent-version retention** (e.g. keep last N versions / 395 days)? This may warrant a dedicated lifecycle rule on `promotions/*`. **Answer:** since we are using promotions/ use a separate lifecycle policy

**Q14 — Cross-region.**
`AWS::Include` modules must load from a same-region bucket, but promotion could target another region.
- **Recommendation:** Scope v1 to **same-region** promotion; expose a `TargetRegion` param but validate/require it equals the current region for now.
- **Q14a:** Is same-region-only acceptable for the initial release? **Answer:** we can use TargetRegion with a default value of "" which will then just have a conditional to use the current region. Each pipeline is in its own region, so the receiving bucket will be serviced by a pipeline that uses the correct region for the includes.

---

## 7. New Parameters (proposed shape)

Pending your answers, I expect these **new, optional, default-off** parameters (names TBD, following `template-parameter-standards`). Listed here so you can react to the surface area before it lands in requirements.

**On the origin/existing templates (additive, non-breaking):**
- `PromoteEnabled` (`true`/`false`, default `false`) — gate for the Promote stage.
- `PromoteApprovalEnabled` (`true`/`false`, default `false`) — the sending approval gate.
- `PromoteTargetStageId` — receiving `StageId`.
- `PromoteTargetDeployEnvironment` (`DEV`/`TEST`/`PROD`).
- `PromoteTargetAccountId` (empty ⇒ same-account promotion).
- `PromoteTargetBucket` — receiving artifacts bucket name (or derive from a target OrgPrefix export? see Q15).
- `PromoteTargetRegion` (default = current region).

**On the new promoted-artifact template (adds, beyond the standard set):**
- `ReleaseApprovalEnabled` (`true`/`false`, default `false`) — the §12 receiving gate.
- Source-object convention params (or derived from Prefix/ProjectId/StageId per Q3).
- Plus its own `PromoteEnabled`/`PromoteTarget*` for chained promotion (`beta → prod`).

- **Q15:** For `PromoteTargetBucket`, prefer an **explicit bucket-name parameter**, or resolve it from a cross-account convention (e.g. the sender is told the receiver's `OrgPrefix` and reconstructs `[org-]cf-artifacts-<targetAcct>-<region>-an`)? Explicit is simpler and less magic; derived is less error-prone for operators. Your call.
- **Q16:** Any objection to the `Promote*` / `Release*` naming, or do you have a preferred vocabulary (e.g. `Handoff`, `Downstream`)?

---

## 8. Modularization Plan (§14)

Because pipeline **stages are inline**, the new stages (Approve, Promote, S3 Source, Release-Approval) will be **inline `!If`-gated stage blocks** in each template, while their **supporting resources become new modules**:

Proposed new modules under `templates/v2/modules/pipeline/`:
- `promote-project.yml` — Promote CodeBuild project (inline framework buildspec).
- `promote-service-role.yml` — its role (incl. cross-account `s3:PutObject` to the target bucket/prefix).
- `promote-log-group.yml` — log group (mirrors existing pattern).
- `promotion-source-event-rule.yml` — S3/EventBridge trigger for the receiving pipeline.
- `promotion-source-event-service-role.yml` — role for that rule to `StartPipelineExecution`.

And a modification to `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml` (+ maybe `s3-artifacts-bucket.yml` for EventBridge notifications).

New parent template (name TBD — see Q17): composed the same way as the existing pipelines.

- **Q17 — New template filename.** The preliminary uses `pipeline-promoted-artifact` (§6.2) while the spec is `pipeline-with-promotion-approval`. I recommend the file `templates/v2/pipeline/template-pipeline-promoted-artifact.yml` (starting at **v0.0.0**, development mode). Confirm the filename.
- **Q18 — Modules are unversioned today; the changed `s3-artifacts-bucket-policy.yml` is consumed by `account-wide-infrastructure.yml` (v0.0.0, dev mode).** Adding an optional statement there is non-breaking. Confirm you're fine modifying that module in place (no module versioning exists yet).

---

## 9. IAM / Service-Role Impact (§15)

**Q19 — `pipeline-mgmt-role.yml` (the CFN service role that deploys pipeline stacks).**
It already permits `events:*`, `codebuild:*`, `codepipeline:*`, `sns:*` on `${Prefix}-*` and worker-role IAM on `${Prefix}-Worker-*`, plus `s3:*` on prefix-scoped buckets. Creating the new Promote CodeBuild project, its worker role (with a cross-account PutObject inline policy), the S3 source event rule, and the release-approval action should **already be covered** by these existing grants.
- **Potential gaps I want to confirm with you rather than assume:**
  - **Q19a:** Creating a worker role whose **inline policy references a bucket in another account** is still just `iam:CreateRole`/`iam:PutRolePolicy` on `${Prefix}-Worker-*` — no new mgmt permission needed. Agree?
  - **Q19b:** Does the mgmt role need anything for **enabling EventBridge notifications on the account-wide bucket** (Q2)? That bucket is managed by `account-wide-infrastructure.yml` (admin-deployed), not by the pipeline mgmt role — so I believe **no** change to `pipeline-mgmt-role` is required for the bucket itself. Confirm the split of responsibility (admin owns the bucket + its cross-account policy; pipeline mgmt role owns the pipeline stack).
  - **Q19c:** The receiving-account `pipeline-mgmt-role` deploys the new promoted-artifact pipeline — same permission set, so likely no change. Confirm.

**Q20 — Worker role runtime permissions (created by the pipeline template, not mgmt).**
- Sending `CodeBuildServiceRole` (Promote): needs cross-account `s3:PutObject` on `arn:aws:s3:::<targetBucket>/promotions/*`. New statement in `promote-service-role.yml`.
- Receiving `CodePipelineServiceRole`: needs `s3:GetObject`/`GetObjectVersion` on the promotion prefix of its own account-wide bucket (already broadly granted via the bucket policy + role, but confirm the pipeline role's own inline policy covers the account-wide bucket, since today `ArtifactStore` uses the per-pipeline `S3ArtifactsBucket`).
- **Q20a:** Is the receiving pipeline's `ArtifactStore` the **same** account-wide artifacts bucket that receives promotions, or a **different** per-pipeline bucket? This affects whether the S3 Source action and the pipeline artifact store are the same bucket and whether extra read grants are needed.

---

## 10. Audit, Manifest & Observability (§10)

**Q21 — Manifest schema.**
The §5.2 schema is a good base. Given Option A, I'd adjust: `source_archive_key` becomes the stable trigger key; add `target_account_id`, `target_region`, `target_bucket`, `source_account_id`, and `commit_sha_full` vs `commit_sha_short`. `post_deploy_passed` is only meaningful when PostDeploy ran.
- **Q21a:** Any required fields beyond §5.2 (e.g. pipeline ARN, approver identity, approval comment)? Note: capturing the **approver's identity** programmatically into the manifest is non-trivial with native approvals — is "approval recorded in CodePipeline history" sufficient, with the manifest capturing only `promoted_by` if/when available?

**Q22 — Is the manifest consumed by anything, or purely audit?**
Under Option A nothing reads it at runtime. Confirming it is **write-only audit** (satisfying §10) keeps the design simple.
- **Q22a:** Confirm no downstream automation must parse the manifest (if something does, that pushes us toward Option B/C).

---

## 11. Testing & Versioning Plan (for requirements.md)

Per the repo steering, I expect the following in `requirements.md`/`tasks.md`. Flagging now so there are no surprises:

- **Version increments (non-breaking, additive):** `template-pipeline.yml` v2.0.22 → v2.0.23; `template-pipeline-github.yml` v2.0.4 → v2.0.5. New `template-pipeline-promoted-artifact.yml` starts at v0.0.0. `account-wide-infrastructure.yml` stays in dev mode (v0.0.0). All new params default off ⇒ **no breaking changes anticipated.**
- **CHANGELOG:** add a new `## v0.0.40 - unreleased` header with entries per template.
- **Tests:** `cfn-lint` validation for all changed/added templates; unit-style checks favored over property-based per testing guidelines. Cross-account behavior itself can't be unit-tested in CI — I'll propose a documented manual integration test (two accounts) as a separate, non-CI task.
- **Docs:** per the documentation steering, add `docs/templates/v2/pipeline/template-pipeline-promoted-artifact-README.md` and update the pipeline category README + the modified templates' docs as the final task.

- **Q23:** Do you agree there are **no breaking changes** (everything additive/default-off), so we stay on PATCH increments + one new v0.0.0 file — i.e. **no** new `-v2-1.yml` files needed? If you foresee a breaking change I've missed, flag it now.
- **Q24:** Should the two-account manual integration test be part of this spec's tasks (documented procedure only), or tracked separately?

---

## 12. Summary of Blockers vs. Nice-to-Confirm

**Must answer before requirements.md (BLOCKERS):**
- **Q1** — trigger/source model (Option A vs B vs C). *Everything downstream depends on this.*
- **Q2** — S3 event detection (EventBridge opt-in on the account-wide bucket).
- **Q8** — the stage matrix / two-approval model.
- **Q12** — cross-account bucket-policy shape and scoping.

**Strongly want to confirm:**
- Q4 (same Prefix/ProjectId), Q6 (reuse SourceArtifact), Q9 (build-only exclusion), Q13 (rollback window), Q17 (filename), Q20a (artifact store == promotion bucket?), Q23 (no breaking changes).

**Lower-risk / naming / detail:**
- Q3, Q5, Q7, Q10, Q11, Q14, Q15, Q16, Q18, Q19a–c, Q21, Q22, Q24.

---

## 13. My Default Assumptions If You Say "Proceed With Your Recommendations"

If you'd rather not answer every question individually, I will proceed under these defaults and note them in `requirements.md`:

1. **Option A** trigger model (stable key + audit manifest; versioning for rollback).
2. EventBridge notifications **opt-in** on the account-wide artifacts bucket.
3. **Two independent, default-off** approval gates (sending "Approve-to-Promote", receiving "Approve-Release") + default-off Promote stage.
4. Promote/Approve added to `template-pipeline.yml` and `-github.yml` only (**not** build-only).
5. New template `template-pipeline-promoted-artifact.yml` @ v0.0.0, composed from new modules.
6. Reuse the existing SourceArtifact as `source.zip`; framework-owned **inline** promote buildspec.
7. Cross-account bucket policy: optional `PromotionSourceAccountId`, scoped to the sender's `*-CodeBuildServiceRole` and the `promotions/*` prefix; empty by default.
8. Reuse existing `PipelineNotificationTopic` for approval emails.
9. Same-region only for v1; one template covers cross-account and same-account via parameters.
10. All changes additive/default-off ⇒ PATCH increments only, new `v0.0.40 - unreleased` changelog section, docs updated as the final task.

Tell me which defaults to override, and I'll fold everything into `requirements.md`.
