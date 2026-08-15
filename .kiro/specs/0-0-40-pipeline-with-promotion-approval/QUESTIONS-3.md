# Cross-Account Serverless CI/CD Promotion
## Pre-Requirements Round 3: Final Clarifications

**Status:** Draft for Developer/Architect Review
**Purpose:** Nail down the approval-flag changes and one lifecycle detail introduced by your `QUESTIONS-2.md` answers, before writing `requirements.md`
**Companion Documents:** [PRELIMINARY.md](./PRELIMINARY.md), [QUESTIONS.md](./QUESTIONS.md), [QUESTIONS-2.md](./QUESTIONS-2.md)
**Date:** 2026-08-13

---

## 0. How to Use This Document

Everything is settled except a few points your **R5a** and **R8a** answers introduced (a new approval-bypass flag, a flipped default, an admin audit CLI, and a lifecycle nuance). These are the last items. Add an **Answer:** line under each `T#`.

If my recommended answers are fine as written, reply **"proceed with the recommendations in QUESTIONS-3"** and I'll generate `requirements.md`.

---

## 1. Approval Model — Reconciling the Two Flags (from your R5a answer)

Your R5a answer changed the approval model from "bundled, always-on" to "**two independent, defaulted-on, but bypassable** gates." Consolidating what you asked for:

- **Sending side (`Approve-to-Promote`):** new flag **`PromoteApprovalRequired`** (default **`true`**). The Promote stage itself is still enabled by a **non-empty `PromoteTargetStageId`**. When promotion is enabled:
  - `PromoteApprovalRequired = true` (default) ⇒ `… → Approve-to-Promote → Promote`.
  - `PromoteApprovalRequired = false` ⇒ `… → Promote` (no human gate on the sending side).
- **Receiving side (`Approve-Release`):** flag **`ReleaseApprovalEnabled`**, default flipped to **`true`**. When `true` ⇒ `Source → Approve-Release → Build`; when `false` ⇒ `Source → Build` (auto-release).

So the fully-automated, zero-gate path requires an operator to deliberately set **both** `PromoteApprovalRequired=false` (sender) **and** `ReleaseApprovalEnabled=false` (receiver) — which is exactly the dangerous combination you want surfaced.

### T1 — Harmonize the two flag names (naming consistency)

The two flags currently have different suffixes (`…Required` vs `…Enabled`), which will read inconsistently in a published template's parameter list. I recommend harmonizing both to the **`…Required`** form, both defaulting to **`true`**:

- `PromoteApprovalRequired` (default `true`) — sending gate.
- `ReleaseApprovalRequired` (default `true`) — receiving gate.

- **T1a:** Harmonize to `PromoteApprovalRequired` / `ReleaseApprovalRequired` (both default `true`)? Or keep your literal names (`PromoteApprovalRequired` + `ReleaseApprovalEnabled`)?
  **Answer:** Yes *Required and default to true for both

### T2 — Parameter descriptions must warn about the bypass consequences

Per your R5a request, the description for each approval flag will explicitly state the consequences of setting it to `false`. Draft language I'll refine for the template:

> **`PromoteApprovalRequired`** — *Default `true`. When `true`, a manual approval gate precedes the Promote stage; a human must approve before an artifact is handed to the target stage/account. Setting this to `false` removes the human gate and promotes automatically once the pipeline succeeds. **If the receiving pipeline also has `ReleaseApprovalRequired=false`, the artifact will build and deploy in the target environment with NO human review at any point — including into PROD stages.** Only disable in fully-trusted, automated-promotion scenarios.*

> **`ReleaseApprovalRequired`** — *Default `true`. When `true`, an incoming promoted artifact waits for manual approval before the receiving pipeline builds/deploys it. Setting this to `false` auto-releases every incoming promotion. **Combined with an upstream `PromoteApprovalRequired=false`, this yields a fully ungated path into this environment.**\*

- **T2a:** Is that the right tone/content for the warnings? Anything you want added (e.g. an explicit callout that DEV/TEST bypass is lower-risk than PROD bypass)?
  **Answer:** The example text is good.

---

## 2. Admin-Ops Audit CLI (from your R5a request)

You asked for a CLI command documented under `docs/admin-ops` that lists all pipelines with approval disabled. I need to pin down scope and detection method to write a concrete requirement.

**Scope**
- **T3a:** Should the audit list pipelines where **either** gate is disabled — i.e. `PromoteApprovalRequired=false` **or** `ReleaseApprovalRequired=false` — flagging which one(s)? Or only the sending `PromoteApprovalRequired=false`? *(My lean: report both, since the ungated-into-PROD risk comes from the receiving `ReleaseApprovalRequired=false`.)*
  **Answer:** Report both, but three different commands. (One for PromoteApprovalRequired, one for ReleaseApprovalRequired, and one for both.)

**Detection method** — two viable approaches:
- **(A) Inspect deployed pipeline structure** — `aws codepipeline list-pipelines` + `get-pipeline`, then report any pipeline that lacks a `Manual` approval action before its Promote/Build stage. *Pro:* reflects reality regardless of how the pipeline was deployed. *Con:* more logic; must recognize Atlantis pipelines specifically.
- **(B) Inspect CloudFormation stack parameters** — enumerate stacks and read the `PromoteApprovalRequired`/`ReleaseApprovalRequired` parameter values. *Pro:* simple, directly reads intent. *Con:* only finds pipelines deployed via these templates as CFN stacks (which is the norm here).

- **T3b:** Prefer **(A)** pipeline-structure inspection, **(B)** CFN-parameter inspection, or a documented command for **both**? *(My lean: (B) as the primary documented command — it's simple and matches how these pipelines are deployed — with a note about (A) as a deeper verification.)*
  **Answer:** Prefer A

**Form factor**
- **T3c:** Is a **documented AWS CLI command / short shell snippet** in `docs/admin-ops/` sufficient, or do you want an actual committed **script** (e.g. under a `scripts/` or `cli/` location) that we also test? *(My lean: documented CLI command + a small copy-paste snippet in `docs/admin-ops/`, no new tested script, to stay in scope. Note: per repo convention I will only create this doc; confirm the `docs/admin-ops/` path — I've seen `docs/maintainer` referenced in your Q24 answer, so tell me which directory is canonical.)*
  **Answer:** documented command, one line script (with pipes or whatever) for admin to copy paste into cli. I was wrong, it should be in the docs/end-user directory as it is ran by the consumer of these templates.

- **T3d:** Q24 (QUESTIONS.md) put the **manual two-account integration test** under `docs/maintainer`. Should the approval-audit CLI doc live in `docs/admin-ops/` (as you said in R5a) while the integration test stays in `docs/maintainer/`, or should both live under the same directory? Confirm the two target directories so I reference them correctly.
  **Answer:** approval-audit CLI doc should actually live in `docs/maintainer/` as it is performed by the maintainer of this repo.

---

## 3. `promotions/` Lifecycle Detail (from your R8a answer)

You answered R8a with "keep **365** days" (I had proposed 395 to match the bucket's existing current-object expiration). To implement the separate `promotions/*` lifecycle rule precisely I need to separate two things:

- **Noncurrent versions** (prior SHAs — the rollback history): **expire after 365 days.** ✅ (your answer)
- **Current object** (the live `source.zip`/`promote.json` the pipeline watches): if the account-wide bucket's existing **395-day current-object expiration** also applies to `promotions/*`, a long-idle current `source.zip` could be deleted, breaking re-run/rollback until the next promotion re-creates it.

- **T4a:** For the **current** object under `promotions/*`, should it (i) **never expire** (recommended — it's the live deploy pointer; only noncurrent versions age out at 365 days), or (ii) expire at 365 days, or (iii) inherit the existing 395-day rule? *(My lean: (i) current never expires; noncurrent expire at 365 days.)*
  **Answer:** current never expires; noncurrent expire at 365 days
- **T4b:** Confirm the `promotions/*` rule also applies to the `promote.json` manifest versions (noncurrent manifests expire at 365 days, current manifest retained), consistent with `source.zip`.
  **Answer:** confirmed, also applies to promote.json

---

## 4. Everything Else Is Locked

For the record, these are settled from Rounds 1–2 and will flow straight into `requirements.md`:

- Option A trigger model; EventBridge opt-in on the account-wide bucket; SHA out of the key, into the manifest + object version.
- Stable keys: `promotions/<prefix>-<projectId>/<stageId>/source.zip` + `…/promote.json`; bucket-name-only scoping; derived, not parameterized, keys.
- Same Prefix/ProjectId across accounts; sender's `PromoteTargetStageId` == receiver's `StageId`.
- Reuse the pipeline SourceArtifact as `source.zip`; framework-owned **inline** promote buildspec (no app-repo override).
- Dedicated `…-PromoteServiceRole` is the **sole** cross-account writer; bucket policy trusts `*-PromoteServiceRole` via Principal-account-list + single `StringLike` condition; `PromotionSourceAccountIds` (`CommaDelimitedList`, empty ⇒ statement omitted); write **and scoped read**; `promotions/*` prefix only; Bucket-Owner-Enforced ownership to be verified in design.
- One receiving template (`template-pipeline-promoted-artifact.yml`, v0.0.0) with an **optional Deploy** (default included); covers cross-account **and** same-account by parameters (empty `PromoteTargetAccountId` ⇒ same account).
- `PromoteTargetBucket` empty ⇒ derive `<S3BucketNameOrgPrefix->cf-artifacts-<TargetAccountId>-<TargetRegion>-an` using the current template's `S3BucketNameOrgPrefix`; `PromoteTargetRegion` empty ⇒ current region.
- Promote/Approve added to all three existing templates (`template-pipeline.yml`, `-github.yml`, `-build-only.yml`); ordering `… → PostDeploy → Approve-to-Promote → Promote` (build-only: `Source → Build → Approve-to-Promote → Promote`).
- **Drop** `PromoteTargetDeployEnvironment` (receiver's own stack is authoritative; omit `target_deploy_env` from the manifest).
- New `Promote*` params grouped in a metadata group **after** the Post Deploy group; `Promote*`/`Release*` vocabulary retained.
- Reuse existing `PipelineNotificationTopic`/email for approval notices; execution-link only.
- Manifest is **write-only audit**; one rolling `promote.json` (history via versioning).
- Admin-owned bucket changes (`account-wide-infrastructure.yml` / `s3-artifacts-bucket-policy.yml` + EventBridge on the bucket); **no** `pipeline-mgmt-role` changes.
- New modules: `promote-project.yml`, `promote-service-role.yml`, `promote-log-group.yml`, `promotion-source-event-rule.yml`, `promotion-source-event-service-role.yml`; modify `s3-artifacts-bucket-policy.yml` (+ `s3-artifacts-bucket.yml` for EventBridge) in place (unversioned modules).
- Versioning: `template-pipeline.yml` v2.0.22→v2.0.23, `-github.yml` v2.0.4→v2.0.5, `-build-only.yml` v2.0.6→v2.0.7; new `template-pipeline-promoted-artifact.yml` @ v0.0.0; `account-wide-infrastructure.yml` stays v0.0.0 (dev). No breaking changes. New `## v0.0.40 - unreleased` CHANGELOG section.
- Tests: cfn-lint for all changed/added templates, unit-style over property-based. Manual two-account integration test documented under `docs/maintainer`. End-user docs for the new template + category README as the final task.

---

## 5. What's Blocking `requirements.md`

Need before I write requirements:
- **T1a** (flag naming), **T3a/T3b/T3c/T3d** (audit CLI scope, method, form factor, doc locations).

Nice to confirm (I have defaults if you skip):
- T2a, T4a, T4b.

Answer these (or reply **"proceed with the recommendations in QUESTIONS-3"**) and I'll generate `requirements.md`.
