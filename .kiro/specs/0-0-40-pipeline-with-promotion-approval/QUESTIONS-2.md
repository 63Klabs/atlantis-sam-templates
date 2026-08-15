# Cross-Account Serverless CI/CD Promotion
## Pre-Requirements Round 2: Follow-up Clarifications

**Status:** Draft for Developer/Architect Review
**Purpose:** Resolve a small set of follow-ups arising from your answers in `QUESTIONS.md`, before writing `requirements.md`
**Companion Documents:** [PRELIMINARY.md](./PRELIMINARY.md), [QUESTIONS.md](./QUESTIONS.md)
**Date:** 2026-08-13

---

## 0. How to Use This Document

Your `QUESTIONS.md` answers settled ~90% of the design. This round handles the remaining items: two technical questions you asked me back, one confirmation of the overall cross-account topology, and a few small decisions your streamlined parameter list surfaced. Add an **Answer:** line under each `R#`.

If you're happy with my recommended answers as written, just reply "proceed with the recommendations in QUESTIONS-2" and I'll write `requirements.md`.

---

## 1. Answers to the Two Questions You Asked Me

### R1 — Promote gets its own service role (re: your Q12a note)

You're right, and this is the correct instinct. Each CodeBuild stage has its own role today: `CodeBuildServiceRole` (Build) and `PostDeployServiceRole` (PostDeploy), named `${Prefix}-Worker-${ProjectId}-${StageId}-{Build|PostDeploy}ServiceRole`.

The Promote stage will get its **own dedicated role**, and **only that role** receives the cross-account `s3:PutObject`/read grant. The Build and PostDeploy roles get **nothing** new — they cannot submit promotion artifacts.

- **Proposed role name:** `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteServiceRole` (module `promote-service-role.yml`).
- **Consequence for the receiving bucket policy:** the cross-account principal it trusts is the sender's **`*-PromoteServiceRole`**, not `*-CodeBuildServiceRole`. I will correct my earlier Q12a wording accordingly. The `StringLike` condition becomes `arn:aws:iam::*:role/*-PromoteServiceRole`.

- **R1a:** Confirm the role name `…-PromoteServiceRole` and that the cross-account bucket policy trusts only `*-PromoteServiceRole` (never the Build/PostDeploy roles).
  **Answer:** Yes, confirmed.

---

### R2 — Can a bucket policy trust a *list* of source accounts without iterating in CFN? (re: your Q12c)

Yes — and cleanly, avoiding the CFN "can't iterate a list to build derived strings" problem you've hit before. The trick is to **not** build per-account role ARNs at all. Instead:

- Put the **list of account IDs** (a `CommaDelimitedList` parameter, e.g. `PromotionSourceAccountIds`) directly into the statement's `Principal.AWS` — CloudFormation accepts a list there natively (each becomes `arn:aws:iam::<acct>:root`, i.e. "any principal in that account").
- Add a **single, non-iterated** `Condition` that constrains the *role name* across all of those accounts:
  ```
  Condition:
    StringLike:
      aws:PrincipalArn: "arn:aws:iam::*:role/*-PromoteServiceRole"
  ```
  The `Principal` list already restricts *which accounts*; the condition restricts *which role*, using one wildcard pattern that needs no per-account expansion (the `*` also spans any `RolePath`).

Net effect: a list of trusted accounts **and** role-pattern scoping, with **zero list iteration** in the template. This resolves your concern and lets us support a list from day one.

- **R2a:** Adopt the **list** parameter `PromotionSourceAccountIds` (`CommaDelimitedList`, default empty ⇒ no cross-account access) using the Principal-list + single-condition pattern above?
  **Answer:** Yes
- **R2b:** Empty list ⇒ the entire cross-account statement is omitted (via a condition), preserving today's behavior exactly. Confirm.
  **Answer:** Yes

> **Note:** This lives in `account-wide-infrastructure.yml` / `s3-artifacts-bucket-policy.yml` (admin-owned), consistent with your Q19b answer. The write also needs `s3:PutObject` **plus** we should decide on object ownership: to ensure the *receiving* account fully owns the promoted object (Q20a intent), the sender's PutObject should include `bucket-owner-full-control`. The bucket already should enforce this via **Bucket Owner Enforced** ownership (ACLs disabled), in which case the receiving account owns all objects automatically and no ACL is needed. I'll verify the bucket's `ObjectOwnership` setting during design; flagging so there are no surprises.

---

## 2. Cross-Account Topology Confirmation

### R3 — Receiving account owns the roles, pipeline, and artifacts (re: your Q20a clarification)

Your description is exactly right, and it's the intended model:

- The **receiving (target) account** hosts the promoted-artifact **pipeline**, all its **worker roles**, the **CloudFormation service role**, and the **account-wide artifacts bucket**.
- After the sender writes `promotions/<prefix>-<projectId>/<targetStageId>/source.zip` into the receiving bucket, **everything needed to proceed lives in the receiving account** — the receiving account owns the artifact and drives Build → Deploy → (PostDeploy) → optional chained Promote.
- The **receiving account-wide bucket holds both** its own pipelines' working artifacts **and** inbound promotions under the **`promotions/*`** prefix.

Given that, the S3 **Source** action of the receiving pipeline and the pipeline's **`ArtifactStore`** both point at that **same** account-wide bucket:

- S3 Source reads `s3://<S3ArtifactsBucket>/promotions/<prefix>-<projectId>/<StageId>/source.zip`.
- `ArtifactStore.Location` = the same `S3ArtifactsBucket` (working artifacts written elsewhere in the bucket, not under `promotions/`).

- **R3a:** Confirm the receiving pipeline uses **one** bucket parameter (`S3ArtifactsBucket`, the account-wide bucket) for **both** its S3 Source location and its `ArtifactStore` — i.e. I should **not** add a separate `PromotionSourceBucket` parameter on the new template.
  **Answer:** Confirmed, it uses one S3ArtifactsBucket for both, do not separate
- **R3b:** Confirm the receiving pipeline's watched key uses its **own** `Prefix`/`ProjectId`/`StageId` (not a "target" — it *is* the target). So the sender must write to the *receiver's* `StageId`, which the sender supplies as `PromoteTargetStageId`. Confirm this pairing (sender's `PromoteTargetStageId` == receiver's `StageId`).
  **Answer:** Correct, sender's `PromoteTargetStageId` == receiver's `StageId`

---

## 3. Parameter & Behavior Decisions from Your Streamlined List

### R4 — Do we still need `PromoteTargetDeployEnvironment`?

Your streamlined parameter list dropped `PromoteTargetDeployEnvironment`, keeping `PromoteTargetStageId`, `PromoteTargetAccountId`, `PromoteTargetRegion`, `PromoteTargetBucket`. That's fine for **triggering** (the receiver already knows its own `DeployEnvironment` from its stack parameters). The only place it mattered was the **audit manifest** field `target_deploy_env` (PRELIMINARY §5.2).

Options:
- **(a) Drop it** — omit `target_deploy_env` from the manifest (or write empty). Simplest; the receiver's own stack is the source of truth for its environment.
- **(b) Keep an optional `PromoteTargetDeployEnvironment`** (default `""`) purely so the sender can record `target_deploy_env` in the audit manifest.

- **R4a:** Prefer (a) drop it, or (b) keep it as an optional audit-only field? *(My lean: (b) — it's one optional string, keeps the manifest complete for your future external audit process, and costs nothing when blank.)*
  **Answer:** a, drop it. the receiver's own stack is the source of truth for its environment. Having the developer supply it on the sender pipeline can introduce errors and is unnecessary.

### R5 — "Approve-to-Promote" and "Promote" are bundled (no separate disable)

From your clarification ("Promote approval and Promote Stage are inclusive… they go together"; a non-empty `PromoteTargetStageId` enables both) and PRELIMINARY §6.1 ("both are included if enabled"), I read this as:

- A **non-empty `PromoteTargetStageId`** enables the **Approve-to-Promote gate _and_ the Promote stage together**, as a single unit. There is **no** option to run Promote without the preceding approval gate.
- The **Approve-Release** gate on the receiving template is the **separate, independent** toggle (`ReleaseApprovalEnabled`, default `false`) — this is the "independently toggleable" from your Q8a answer.

- **R5a:** Confirm there is **no** "promote without approval" mode (i.e. we will **not** add a separate `PromoteApprovalEnabled` flag). Approval is always present when promotion is enabled.
  **Answer:** I want the opposite default (`ReleaseApprovalEnabled`, default `true`). 

> If you ever want fully-automated promotion (no human gate), say so now — it's cheap to add a `PromoteApprovalEnabled=true` default flag, but I won't add it unless you want that degree of freedom.
**RESPONSE:** Okay, let's add it but name it `PromoteApprovalRequired=true` However, I would like a cli command listed in docs/admin-ops that can list all the pipelines that have it set to false. Also, the description should explicitly state the consequences for setting it to false (especially if the receiving pipeline auto approves incoming artifacts)

### R6 — Pipeline SourceArtifact naming (re: your note on Confirmation #6)

You flagged that pipeline artifacts drop the Prefix (`${ProjectId}-${StageId}-SourceArtifact`) and asked whether this hurts promotion and whether to standardize on `${Prefix}-${ProjectId}-${StageId}-SourceArtifact`.

Findings:
- **It does not affect promotion.** CodePipeline artifact names are **internal to a single pipeline execution** — they label artifacts handed between stages within one pipeline and never cross the account/S3 boundary. What crosses is the `source.zip` object under `promotions/*`, whose S3 key we control independently. So the current naming is functionally safe for this feature.
- **Renaming is cosmetic and low-risk but not free.** Changing an artifact name is an **in-place pipeline update** (no resource replacement, no data loss). However, it touches **all three** existing templates and every stage's `InputArtifacts`/`OutputArtifacts`, and it is **unrelated** to the promotion feature. Per the version-control rules it's a non-breaking PATCH-level change, but bundling an unrelated rename into this spec widens the blast radius of testing.

Recommendation: **keep the rename out of this spec** to keep the promotion change focused, and track it as a separate small cleanup. If you'd rather standardize now, I'll fold it in as an explicit, separate task group with its own version bumps.

- **R6a:** Exclude the SourceArtifact rename from this spec (recommended), or include it as a separate task set that renames artifacts to `${Prefix}-${ProjectId}-${StageId}-SourceArtifact` (and Build/PostDeploy artifacts likewise) across all three existing templates?
  **Answer:** Exclude the rename from this spec

### R7 — Build-only stage ordering (re: your Q9a "include build-only")

Build-only has only `Source → Build` (no Deploy/PostDeploy; you noted post-deploy-style work happens inside the same Build container for CDK/script/CLI use cases). So the added stages append after Build:

- `Source → Build → Approve-to-Promote → Promote` (when `PromoteTargetStageId` is set).

- **R7a:** Confirm that ordering for `template-pipeline-build-only.yml`.
  **Answer:** Confirmed
- **R7b:** The **receiving** side of a build-only promotion would use the **new `template-pipeline-promoted-artifact.yml`** too, but that template always contains Build → Deploy. For a build-only-style workload (no deploy), would you (i) still use the promoted-artifact template with Deploy present-but-empty/skippable, or (ii) expect a build-only *flavor* of the receiving template? *(My lean: keep one receiving template with an optional/skippable Deploy so we don't fork it; but I want your call since it affects the new template's stage conditionals.)*
  **Answer:** Good catch. We'll keep one receiving template with an optional deploy (default is include it).

---

## 4. Minor Confirmations (low risk)

### R8 — `promotions/` lifecycle rule specifics

Per your Q13a answer (separate lifecycle policy for `promotions/`), I propose: on the `promotions/*` prefix, **retain noncurrent versions for the same 395-day window** as current-object expiration (so rollback range == retention range), and expire current objects at 395 days as well.

- **R8a:** Is "noncurrent versions retained 395 days, keep all versions within that window" the right rollback policy, or do you prefer a **count-based** cap (e.g. keep the last N=10 noncurrent versions) instead of / in addition to the time-based rule?
  **Answer:** keep 365 days.

### R9 — Manifest object location & naming

The audit manifest is written next to the trigger object:
`promotions/<prefix>-<projectId>/<targetStageId>/promote.json` (single file, overwritten each promotion; full history preserved by bucket versioning).

- **R9a:** One rolling `promote.json` (history via versioning) is fine, or do you want per-execution manifest filenames (e.g. `promote-<timestamp>-<shortsha>.json`) for easier external audit listing? *(My lean: rolling `promote.json` + versioning, consistent with the source.zip approach.)*
  **Answer:** s3 versioning is fine. One rolling `promote.json` (history via versioning) is fine

---

## 5. Summary — What's Blocking `requirements.md`

Genuinely need before I write requirements:
- **R1a** (promote role is the sole cross-account writer), **R2a** (list-of-accounts approach), **R3a/R3b** (single-bucket receiving topology), **R5a** (approval bundled with promote), **R6a** (include or exclude the artifact rename).

Nice to confirm (I have sensible defaults if you skip):
- R2b, R4a, R7a, R7b, R8a, R9a.

Answer the blockers (or say "proceed with the recommendations in QUESTIONS-2") and I'll generate `requirements.md`.
