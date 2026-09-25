# v0.0.44 Planning — Bedrock Media (Large Object) Logging + Log Prefix Segmentation & Service Lockdown

> **Status:** Pre-requirements planning / discovery. This document captures findings, proposed direction, concerns, and open questions. We will iterate here before writing `requirements.md`. Nothing below is final.
>
> **Iteration note:** §5 questions have been answered by the maintainer (inline). §8 (Round 2) records the locked decisions, verified answers to the two AWS-feasibility questions those answers raised, and a short set of new follow-ups. Read §8 for the current state of the plan; §3/§4 have been updated to match.

## 1. Goal (as understood)

1. **Bedrock media/large-object logging to S3.** Route Bedrock model invocation *image/video/large binary* payloads (which cannot go to CloudWatch Logs, added in v0.0.43) to the account-wide logging bucket created by `account-wide-infrastructure.yml`.
2. **Provider-prefixed log organization.** Reorganize everything that writes into the account-wide logging bucket so each producer writes under its own top-level prefix (`cloudfront/`, `bedrock/`, `s3access/`, `cf-artifacts/`, ...), enabling prefix-scoped lifecycle rules.
3. **Per-prefix lifecycle expiration.** Default each prefix to a shared `LogExpirationInDays`, but allow a prefix to opt into its own retention (e.g. Bedrock media → `BedrockLargeObjectLogExpirationInDays`).
4. **Per-service bucket-policy lockdown.** Tighten the logging bucket policy so each writer principal can only write to *its own* prefix (CloudFront → `cloudfront/`, Bedrock → `bedrock/`, S3 access logs → `s3access/`, etc.), instead of the current whole-bucket (`/*`) grant.
5. **New toggles & alternate destination.** Add `EnableBedrockLargeObjectLogging` and an alternate S3 destination parameter (mirroring the existing artifacts-bucket pattern), and enforce the existing rule that *either* `EnableS3AccessLogBucket` is `true` *or* an alternate destination is supplied.
6. **Retrofit producer templates** (s3-oac-for-cloudfront, s3 access logging, network cloudfront, artifacts) to use the new, consistent prefixes.

## 2. Current-state findings (verified against the code)

### 2.1 The account-wide logging bucket
- Bucket module: `templates/v2/modules/s3-access-logs/s3-access-log-bucket.yml` (`Condition: EnableS3AccessLogBucket`, `Retain`/`Retain`, AES256 + bucket keys, Versioning `Suspended`).
  - Name: `${S3BucketNameOrgPrefix}-access-logs-${AccountId}-${Region}-an` or `access-logs-${AccountId}-${Region}-an`.
  - **Single, bucket-wide lifecycle rule** `DeleteOldLogs` → `ExpirationInDays: !Ref LogExpirationInDays`. No per-prefix rules today.
  - Public access block: `BlockPublicAcls = !If [EnableLegacyCloudFrontLogs, false, true]`; others `true`.
  - Ownership: `!If [EnableLegacyCloudFrontLogs, BucketOwnerPreferred, AWS::NoValue]` (i.e. **ACLs enabled only for legacy CloudFront**).
- Bucket policy module: `templates/v2/modules/s3-access-logs/s3-access-log-bucket-policy.yml`. Three statements:
  1. `DenyNonSecureTransportAccess` (Deny `s3:*` unless TLS).
  2. `AllowS3LogDelivery` — `logging.s3.amazonaws.com` `s3:PutObject` on **`${bucket.Arn}/*`** (whole bucket), condition `aws:SourceAccount = AccountId`.
  3. `AllowCloudFrontLogDelivery` (only when `EnableLegacyCloudFrontLogs`) — `delivery.logs.amazonaws.com` `s3:PutObject` on **`${bucket.Arn}/*`**, condition `s3:x-amz-acl = bucket-owner-full-control`.
  - **No prefix scoping and no Bedrock principal today.**
- Canonical/standalone twin: `templates/v2/storage/template-storage-s3-access-logs.yml` (prefix+project scoped, YAML shorthand, marked deprecated). **Must be kept in sync** per `.kiro/steering/s3-access-logs-module-sync.md`.
- Parent wiring: `account-wide-infrastructure.yml` v2.0.2 declares the resources `AccessLogBucketRegional` / `AccessLogBucketPolicy`, the params `LogExpirationInDays` (Number, default 180, 1–365) and `AllowLegacyCloudFrontLogs`, and exports `${OrgPrefix}-S3-AccessLog-Bucket-Name` / `-Arn`.

### 2.2 Everything that writes logs into a bucket today (prefix inventory)
| Producer | File | Delivery mechanism / principal | Current prefix | Destination selection |
|---|---|---|---|---|
| Account-wide artifacts bucket | `modules/account-wide/s3-artifacts-bucket.yml` | S3 server access logs (`logging.s3.amazonaws.com`) | `cf-artifacts/` | 3-tier: `S3LogBucketName` → `AccessLogBucketRegional` → none |
| CloudFront distribution | `network/template-network-route53-cloudfront-s3-apigw.yml` | CloudFront **legacy** standard logs (`delivery.logs.amazonaws.com`, ACL) | `cloudfront/${Prefix}-${ProjectId}-${StageId}` | explicit `S3LogBucketName` only |
| OAC origin bucket | `storage/template-storage-s3-oac-for-cloudfront.yml` | S3 server access logs | `${OrgPrefix}${Prefix}-${ProjectId}-${Region}-${AccountId}/` (computed slug) | explicit `S3LogBucketName` only |
| S3 artifacts (standalone) | `storage/template-storage-s3-artifacts.yml` | S3 server access logs | `cf-templates-...` slug | explicit `S3LogBucketName` only |
| S3 devops (standalone) | `storage/template-storage-s3-devops.yml` | S3 server access logs | `${Prefix}-${ProjectId}-...-an` slug | explicit `S3LogBucketName` only |
| Cache-data bucket | `modules/cache-data/cache-s3-bucket.yml` | **none** (no access logging) | n/a | n/a |

**Observation:** prefixes are inconsistent and not provider-organized. Only the account-wide artifacts bucket auto-targets the account-wide logging bucket; every other producer requires an explicit `S3LogBucketName`. There is no `bedrock/` or `s3access/` prefix anywhere yet.

### 2.3 Current Bedrock invocation logging (v0.0.43)
- `modules/account-wide/bedrock-cloudwatch-log-group.yml`: log group `/aws/bedrock/${OrgPrefix}-ModelInvocations`, `RetentionInDays: !Ref BedrockInvocationLogExpirationInDays` (CloudWatch retention, allowed-values list, default 180), optional KMS.
- `modules/account-wide/bedrock-cloudwatch-role.yml`: role assumed by `bedrock.amazonaws.com` (confused-deputy guarded), inline policy grants **only** `logs:CreateLogStream`/`logs:PutLogEvents` on the log stream. **No S3 permissions.**
- Activation is a **manual** post-deploy CLI step (Bedrock has no CFN resource for `PutModelInvocationLoggingConfiguration`). Output `BedrockModelInvocationLoggingEnableCommand` emits: `{"cloudWatchConfig":{...},"textDataDeliveryEnabled":true,"embeddingDataDeliveryEnabled":true,"imageDataDeliveryEnabled":false,"videoDataDeliveryEnabled":false}`.
- Image/video are deliberately `false` "because binary payloads cannot be delivered to CloudWatch Logs without an S3 large data delivery target" — **exactly the gap v0.0.44 fills.**
- Admin doc: `docs/admin-ops/bedrock-model-invocation-logging.md` (has a "Why text and embedding only?" section and Known Limitations that will need updating).

### 2.4 Verified AWS behavior for Bedrock → S3 (from AWS docs)
[AWS: Model invocation logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) — content rephrased for compliance with licensing restrictions:
- S3 log delivery is authorized by a **bucket policy on the `bedrock.amazonaws.com` service principal** granting `s3:PutObject`, **not** by the CloudWatch role. So the existing Bedrock role needs *no* S3 change.
- The object key layout is fixed by Bedrock: `bucketName/{keyPrefix}/AWSLogs/{accountId}/BedrockModelInvocationLogs/*`. The only user-controlled segment is `keyPrefix` → setting it to `bedrock` yields objects under `bedrock/AWSLogs/...`, which lines up cleanly with the requested `bedrock/` prefix and a `Filter.Prefix: bedrock/` lifecycle rule.
- Recommended conditions: `aws:SourceAccount = {accountId}` and `aws:SourceArn` like `arn:aws:bedrock:{region}:{accountId}:*`.
- The bucket/region/account must match; and **bucket ACLs must be disabled** for the bucket policy to take effect.
- Two S3 config shapes exist: top-level `s3Config` (send *all* logs to S3) vs `cloudWatchConfig.largeDataDeliveryS3Config` (small data → CloudWatch, large/binary → S3). For "media" we want the latter so existing text/embedding-to-CloudWatch behavior is preserved.
- KMS (SSE-KMS) buckets additionally need `kms:GenerateDataKey` for `bedrock.amazonaws.com` on the key. The account-wide logging bucket is AES256 (SSE-S3) by default, so no KMS work unless a key is introduced.

## 3. Proposed direction (draft — for discussion)

### 3.1 Prefix taxonomy (updated per §8 decisions)
Adopt top-level provider prefixes in the account-wide logging bucket, with all S3 server access logs consolidated under `s3access/` and sub-typed:
- `cloudfront/` — CloudFront standard logging **v2** (vended logs to S3; Bedrock-free path). Objects land under `cloudfront/AWSLogs/{accountId}/CloudFront/...`.
- `s3access/` — all S3 server access logs, sub-segmented by producer type then source bucket name:
  - `s3access/cf-artifacts/<bucket-name>/`
  - `s3access/cloudfront-oac/<bucket-name>/`
  - `s3access/devops/<bucket-name>/`
  - `s3access/apps/<bucket-name>/` — general Atlantis application buckets (term TBD: `apps` / `sam-apps` / `applications` / `general` — see §8 Q1)
- `bedrock/` — Bedrock large-object/media invocation logs (Bedrock appends `AWSLogs/{accountId}/BedrockModelInvocationLogs/`).

### 3.2 Lifecycle: one rule per prefix (updated)
Replace the single `DeleteOldLogs` rule with one rule per prefix/sub-prefix, each with a `Filter.Prefix`:
- `cloudfront/` → `ExpirationInDays: !Ref LogExpirationInDays` (shared default for non-specific prefixes).
- `s3access/cf-artifacts/`, `s3access/cloudfront-oac/`, `s3access/devops/`, `s3access/apps/` → **four separate rules**, all currently referencing `!Ref S3AccessLogExpirationInDays` (separate rules now so finer-grained per-type knobs can be split out later without restructuring).
- `bedrock/` → `ExpirationInDays: !Ref BedrockLargeObjectLogExpirationInDays` (default 90).

> Note: `LogExpirationInDays` is an **S3 lifecycle** value (days), not a CloudWatch retention value. CloudWatch retention for Bedrock text/embedding logs remains the separate `BedrockInvocationLogExpirationInDays` param.

### 3.3 Bucket policy: per-principal, per-prefix (updated)
Rewrite the policy statements to scope each `Resource` ARN to the owning prefix, and **drop the legacy CloudFront/ACL statement entirely** (moving to v2):
- `logging.s3.amazonaws.com` (all S3 server access logs) → `.../s3access/*`, condition `aws:SourceAccount = AccountId`. (Per-source-bucket path binding and tag gating are not possible — see §4.2 / §8 A1.)
- `delivery.logs.amazonaws.com` (CloudFront v2 vended logs) → `.../cloudfront/*`, conditions `aws:SourceAccount` + `aws:SourceArn` (the CloudFront delivery ARN).
- `bedrock.amazonaws.com` (conditional on `EnableBedrockLargeObjectLogging`) → `.../bedrock/AWSLogs/${AccountId}/BedrockModelInvocationLogs/*`, conditions `aws:SourceAccount` + `aws:SourceArn` (`arn:aws:bedrock:{region}:{accountId}:*`).
- Keep `DenyNonSecureTransportAccess`.
- The **main** logging bucket ownership becomes **`BucketOwnerEnforced` always** (ACLs disabled). This satisfies S3 access logs, CloudFront **v2**, and Bedrock. **Superseded update (see §9):** rather than removing `AllowLegacyCloudFrontLogs`, it is repurposed to provision a **separate ACL-enabled `cloudfront-logs-legacy` bucket** so CloudFront **v1** remains usable (especially outside us-east-1). The legacy CloudFront policy statement moves to that separate bucket; the main bucket no longer carries any ACL/ownership toggle.

### 3.4 New / changed parameters (account-wide-infrastructure.yml)
- `EnableBedrockLargeObjectLogging` (String, `true`/`false`, default `false`) — new "S3 Bedrock Large Object Logs" group.
- `BedrockLargeObjectLogExpirationInDays` (Number, 1–365, default `90`) — S3 lifecycle for the `bedrock/` prefix. **Distinct** from the CloudWatch `BedrockInvocationLogExpirationInDays`.
- `BedrockLargeObjectLogBucketName` (optional S3 bucket name, `S3LogBucketName`-style pattern) — alternate external destination; takes precedence over the account-wide bucket.
- `S3AccessLogExpirationInDays` (Number, 1–365, default TBD — propose match `LogExpirationInDays` = 180) — drives the four `s3access/*` lifecycle rules.
- **`AllowLegacyCloudFrontLogs` — repurposed, not removed (see §9).** When `true`, the account-wide stack provisions a dedicated ACL-enabled `cloudfront-logs-legacy` bucket (+ policy) for CloudFront v1 standard logs, instead of toggling ACLs on the main bucket.

### 3.5 "Either enable the bucket or provide an alternate" enforcement
Use the CloudFormation `Rules` section to assert: if `EnableBedrockLargeObjectLogging = true`, then `EnableS3AccessLogBucket = true` **or** `BedrockLargeObjectLogBucketName` is non-empty. (Same guard should be considered for the existing artifacts-bucket logging, which currently just silently falls back to no logging.)

### 3.6 Activation command output
When `EnableBedrockLargeObjectLogging = true`, extend `BedrockModelInvocationLoggingEnableCommand` to include `cloudWatchConfig.largeDataDeliveryS3Config` (bucket + `keyPrefix: bedrock`) and flip `imageDataDeliveryEnabled`/`videoDataDeliveryEnabled` to `true`. Keep text/embedding on CloudWatch. Activation stays a manual CLI step (unchanged constraint).

### 3.7 Producer retrofits (updated)
All producer buckets (except the logging bucket itself and cache-data) get: (a) the new `s3access/<type>/<bucket-name>/` server-access `LogFilePrefix`, and (b) a destination-selection precedence of `S3LogBucketName` → imported `${OrgPrefix}-S3-AccessLog-Bucket-Name` → none (mirroring the account-wide artifacts bucket, and the existing `S3ArtifactsBucket` import-fallback pattern). This requires an `OrgPrefix` param on the standalone templates that lack one.
- Account-wide artifacts bucket (`modules/account-wide/s3-artifacts-bucket.yml`) → `s3access/cf-artifacts/<bucket-name>/`.
- OAC origin bucket (`template-storage-s3-oac-for-cloudfront.yml`) → `s3access/cloudfront-oac/<bucket-name>/` + import-fallback.
- Devops bucket (`template-storage-s3-devops.yml`) → `s3access/devops/<bucket-name>/` + import-fallback.
- Standalone artifacts (`template-storage-s3-artifacts.yml`) → `s3access/cf-artifacts/<bucket-name>/` (pending §8 Q4 scope confirm) + import-fallback.
- CloudFront network template (`template-network-route53-cloudfront-s3-apigw.yml`) → **support both v1 and v2** (see §9). v1 keeps the inline `DistributionConfig.Logging` block pointed at the legacy ACL bucket (works from any region); v2 uses CloudWatch Logs delivery resources targeting the `cloudfront/` prefix (us-east-1 only — see §9 constraint).
- Cache-data bucket → unchanged (no server access logging), per §5 Q4.

## 4. Concerns / risks

1. **ACL conflict — RESOLVED via two buckets (§9), keeping v1 available.** The ACL-requiring writer (CloudFront v1) gets a dedicated ACL-enabled `cloudfront-logs-legacy` bucket, while the main logging bucket stays `BucketOwnerEnforced` (ACLs off) for S3 access logs, CloudFront v2, and Bedrock. This avoids forcing us-east-1-only v2 on non-us-east-1 deployments (e.g. the maintainer's us-east-2 account) and sidesteps the ACL/Bedrock contradiction cleanly.
2. **Single principal for all S3 access logs — segmentation is best-effort, not policy-enforced (verified).** All S3 server access logs are delivered by the same principal (`logging.s3.amazonaws.com`), and the only usable conditions are `aws:SourceAccount` and `aws:SourceArn` (the source *bucket* ARN); the destination policy scopes to `Resource: .../PREFIX*`. Consequences (verified against AWS docs): (a) the `s3access/<type>/<bucket-name>/` path is set by each producer's own `LogFilePrefix` and **cannot be cryptographically bound** to the actual writer unless the shared policy enumerates every source bucket ARN (not feasible for open-ended project buckets); (b) there is **no condition key exposing the source bucket's tags**, so gating `s3access/apps/` (or `general`) by an `Atlantis=application-infrastructure` tag is **not possible** via bucket policy. Realistic lockdown = principal + `s3access/*` resource scope + `aws:SourceAccount`, optionally tightened with an `aws:SourceArn` ArnLike pattern keyed to the naming convention (e.g. `arn:aws:s3:::*-an`). See §8 A1 / Q2.
3. **Tightening the policy can break existing deliveries.** Any deployment already logging to a now-disallowed prefix (e.g. the OAC computed slug at bucket root) will have deliveries *denied* after the policy is scoped, until its producer stack is updated to the new prefix. This is effectively a coordinated migration and leans toward **breaking-change** territory for `account-wide-infrastructure.yml` and the standalone access-logs template. Needs a migration note and version-bump decision (PATCH vs new MINOR file per template-version-control).
4. **Bucket semantics/naming drift.** The bucket is named `access-logs-*` and described as "S3 server access logs," but will now also hold CloudFront and Bedrock media logs. Renaming the bucket would replace it (data-loss / breaking). Recommend keeping the name and updating descriptions/docs to "account-wide logs bucket." Confirm.
5. **Two Bedrock retention knobs.** `BedrockInvocationLogExpirationInDays` (CloudWatch, allowed-values) vs new `BedrockLargeObjectLogExpirationInDays` (S3, 1–365). Risk of user confusion; needs crisp descriptions.
6. **Alternate/external Bedrock bucket can't be policy-wired by this stack.** When `BedrockLargeObjectLogBucketName` points to an external bucket, we cannot attach the required `bedrock.amazonaws.com` bucket policy to it — the admin must do that themselves (same caveat as `S3LogBucketName` for artifacts). Document clearly.
7. **Module/standalone sync + fan-out.** Changes touch: 2 s3-access-logs modules **and** the standalone `template-storage-s3-access-logs.yml` (sync steering), plus the artifacts module, OAC template, network CloudFront template, and possibly the devops/standalone artifacts templates. Each versioned template gets a version bump + README update per steering. Non-trivial surface area.
8. **Media log sensitivity & cost.** Image/video invocation payloads are large and may contain sensitive generated content; the bucket is `Retain`. Retention defaults and encryption guidance should be deliberate.
9. **Sec review:** the `bedrock/` grant must include both `aws:SourceAccount` and `aws:SourceArn`; the resource ARN should be scoped to the `.../BedrockModelInvocationLogs/*` path, not the whole `bedrock/` prefix, to be tight.

## 5. Clarifying questions (please weigh in)

1. **`cf-artifacts` placement:** keep it as a top-level sibling prefix, or nest all S3 server access logs under `s3access/` (e.g. `s3access/cf-artifacts`, `s3access/<project-oac>/`)? The goal statement lists them separately, which I've assumed — confirm. **Answer:** list all under s3access. So we can separate lifecycles, can we use: `s3access/cf-artifacts/<bucket-name>`, `s3access/cloudfront-oac/<bucket-name>/`, `s3access/devops/<bucket-name>`, `s3access/general/<bucket-name>`. Also, would it be possible to ensure that the logs being written to `s3access/<type>/<bucket-name>` came from the named bucket through a policy? I'm not sure if that is possible from a permissions standpoint. Right now there are no "general" buckets in the current templates, which is fine. These would be for the atlantis applications. General doesn't have to be the term, it could be "applications" or "sam-apps" or "apps". I'm open to suggestions. If access to "general" prefix could be limited to producers with the "Atlantis=application-infrastructure" tag that would be great.
2. **CloudFront path forward:** stay on **legacy** standard logging (ACL-based, keeps the ACL conflict in #4.1), or take this release as the opportunity to move CloudFront to **standard logging v2** so one ACL-disabled bucket cleanly serves CloudFront + S3 access + Bedrock? (Bigger scope, but resolves the core ACL tension.) **Answer:** I would like to move forward with moving to v2. We are still in beta with limited release so we may as well not use legacy. Also we have minimal deployments so it isn't hard to run the update for existing cloudfront stacks. My question is what will this take? Originally i had found little documentation for how the cloudformation template for cloudfront would be structured for v2.
3. **Per-prefix expiration granularity:** is a single shared `LogExpirationInDays` for all non-Bedrock prefixes plus a Bedrock-specific knob sufficient, or do you want individual params per prefix now (`CloudFrontLogExpirationInDays`, `S3AccessLogExpirationInDays`, ...)? I lean shared-default + Bedrock override. **Answer:** Shared default `LogExpirationInDays` used by CloudWatch can be used for non specific prefixes. For `s3access` use `S3AccessLogExpirationInDays` for 4 separate lifecycles (cloudfront-oac, cf-artifacts, devops, general) as we may implement finer grained controls down the road, and then a Bedrock-media-specific one for now.
4. **Auto-fallback for producers:** should OAC/devops/standalone buckets auto-target the account-wide logging bucket via export import (like the artifacts bucket), or continue requiring an explicit `S3LogBucketName`? **Answer** Yes, all buckets (except logging and cache-data) should auto-target the account-wide logging bucket via export import like the artifacts bucket. They should allow an `S3LogBucketName` as well. 
5. **Breaking change tolerance:** are we willing to tighten the bucket policy in place (coordinated migration, possible temporary delivery denial for out-of-date stacks), or must this be strictly additive/backward compatible? This drives whether `account-wide-infrastructure.yml` / the standalone template stay same-file (PATCH) or spawn new MINOR versioned files. **Answer:** We are in limited deployment right now so it is managable to break this and perform updates.
6. **Defaults:** `EnableBedrockLargeObjectLogging` default `false` (opt-in, given cost/sensitivity) — agree? And what default for `BedrockLargeObjectLogExpirationInDays` (e.g. 90)? **Answer:** Yes, false and 90 days is good.
7. **Bedrock S3 shape:** confirm we use `cloudWatchConfig.largeDataDeliveryS3Config` (hybrid: text/embedding stay in CloudWatch, large/binary to S3) rather than top-level `s3Config` (everything to S3). **Answer** Yes, hybrid, text/embedding stay in CloudWatch
8. **Scope of producers this release:** which producer templates must be retrofitted in v0.0.44 vs deferred? (Account-wide artifacts + OAC + network CloudFront feel core; standalone devops/artifacts could follow.) **Answer:** I want to bring OAC, artifacts, and devops in scope

## 6. Anticipated file surface (for scoping, not final)
- `templates/v2/account/account-wide-infrastructure.yml` (params, conditions, Rules, policy wiring, activation output; version bump)
- `templates/v2/modules/s3-access-logs/s3-access-log-bucket.yml` (per-prefix lifecycle)
- `templates/v2/modules/s3-access-logs/s3-access-log-bucket-policy.yml` (per-principal/prefix scoping + Bedrock statement)
- `templates/v2/storage/template-storage-s3-access-logs.yml` (sync counterpart)
- `templates/v2/modules/account-wide/s3-artifacts-bucket.yml` (prefix confirm/adjust)
- `templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml` (→ `s3access/` prefix)
- `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml` (prefix confirm; possible v2 logging)
- `templates/v2/storage/template-storage-s3-devops.yml`, `template-storage-s3-artifacts.yml` (optional prefix retrofit)
- `docs/admin-ops/bedrock-model-invocation-logging.md` (media/S3 activation section)
- `docs/templates/v2/...` READMEs for each touched template + category READMEs
- `CHANGELOG.md` (v0.0.44 entries at spec completion)

## 7. Next steps
1. Resolve the §5 questions (especially the ACL/CloudFront-v2 decision in Q2 and breaking-change tolerance in Q5).
2. Draft `requirements.md` (EARS) once direction is agreed.
3. Then `design.md` (policy statements, lifecycle rules, activation JSON, migration notes) and `tasks.md`.

## 8. Round 2 — locked decisions, verified answers, and new follow-ups

### 8.1 Locked decisions (from §5 answers)
| # | Decision |
|---|---|
| Q1 | Consolidate all S3 server access logs under `s3access/`, sub-typed: `cf-artifacts`, `cloudfront-oac`, `devops`, and a general bucket type (term TBD). Path: `s3access/<type>/<bucket-name>/`. |
| Q2 | Move CloudFront off legacy standard logging to **standard logging v2**. Acceptable to update the few existing CloudFront stacks. |
| Q3 | Three retention knobs: `LogExpirationInDays` (shared default, e.g. `cloudfront/`), `S3AccessLogExpirationInDays` (four separate `s3access/*` rules), `BedrockLargeObjectLogExpirationInDays` (bedrock, 90). |
| Q4 | All buckets except logging + cache-data auto-target the account-wide logging bucket via export import, with an `S3LogBucketName` override. |
| Q5 | Breaking changes acceptable (limited/beta deployment). |
| Q6 | `EnableBedrockLargeObjectLogging` default `false`; Bedrock media expiration default `90` days. |
| Q7 | Hybrid Bedrock delivery: text/embedding → CloudWatch, large/binary → S3 via `cloudWatchConfig.largeDataDeliveryS3Config`. |
| Q8 | In scope: OAC, artifacts, devops (+ CloudFront network template, since we're moving it to v2). |

### 8.2 Verified answer A1 — can we bind the `s3access/<type>/<bucket-name>` path to the real source bucket, or gate `apps`/`general` by tag?
Verified against the [S3 server access logging bucket-policy guidance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-server-access-logging.html) (content rephrased for compliance):
- The destination bucket policy grants `logging.s3.amazonaws.com` `s3:PutObject` on `Resource: arn:aws:s3:::<dest-bucket>/<prefix>*`, with only two useful conditions: `aws:SourceArn` (the **source bucket** ARN) and `aws:SourceAccount` (source account id).
- **Per-bucket path binding is not achievable** in a shared account-wide policy: nothing maps the source bucket name into the object key, so we cannot enforce that a write to `s3access/devops/<bucket-name>/` actually originated from `<bucket-name>` unless we add one statement per enumerated source-bucket ARN — impractical for open-ended, project-created buckets.
- **Tag-gating is not achievable:** server-access-log delivery exposes no condition key for the source bucket's tags (no `aws:PrincipalTag` for a service principal, no source-resource-tag key). So restricting `s3access/apps/` to buckets tagged `Atlantis=application-infrastructure` cannot be done in the bucket policy.
- **What we *can* do:** scope the grant to `Resource: .../s3access/*` + `aws:SourceAccount = AccountId`, and optionally add an `aws:SourceArn` `ArnLike` pattern that matches the Atlantis bucket naming convention (e.g. `arn:aws:s3:::*-an`) to keep out non-conforming buckets. The `<type>/<bucket-name>` structure remains an organizational convention enforced by each producer's `LogFilePrefix`, not by the destination policy. Net: strong account-level and prefix-level lockdown; no true per-bucket or per-tag lockdown for S3 access logs. (Bedrock and CloudFront v2, by contrast, *do* get real `aws:SourceArn` binding to the Bedrock/CloudFront delivery ARN.)

### 8.3 Verified answer A2 — what does moving CloudFront to standard logging v2 take?
Verified against the [CloudFront standard logging](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logging.html) docs (CloudFront v2 "uses CloudWatch vended logs to deliver access logs"):
- **Distribution change:** remove the inline `DistributionConfig.Logging` block. In v2 the distribution no longer names a log bucket; delivery is wired by separate resources.
- **Three new CloudWatch Logs resources** (per distribution → S3):
  - `AWS::CloudWatchLogs::DeliverySource` — `ResourceArn` = the CloudFront distribution ARN, `LogType` = `ACCESS_LOGS`.
  - `AWS::CloudWatchLogs::DeliveryDestination` — `DestinationResourceArn` = the account-wide logging bucket ARN, plus output-format config.
  - `AWS::CloudWatchLogs::Delivery` — joins the source + destination; `S3DeliveryConfiguration` sets the suffix path (and optional Hive-compatible partitioning). This is where we steer objects under the `cloudfront/` prefix.
- **Destination bucket policy:** grant `delivery.logs.amazonaws.com` `s3:PutObject` scoped to `.../cloudfront/*` with `aws:SourceAccount` + `aws:SourceArn` (the delivery ARN). **No ACLs / no `BucketOwnerPreferred`** — this is the piece that removes the legacy ACL requirement.
- **Region pinning (design concern):** CloudFront is global; its logging-delivery resources must be created in **us-east-1**. The account-wide logging bucket is *regional*. So CloudFront v2 access logs effectively require either the account-wide stack (and its bucket) deployed in us-east-1, or the delivery resources in us-east-1 pointing at a us-east-1 bucket. Needs a concrete multi-region decision (see Q3 below).
- **Doc gap the maintainer hit** is expected: the CloudFront guide describes console/CLI setup; the CloudFormation shape lives under the generic CloudWatch Logs "vended logs / delivery" resources rather than under CloudFront. We'll capture the exact resource wiring in `design.md`.

### 8.4 New follow-up questions (Round 2)
1. **General bucket-type term.** Proposal: `s3access/apps/`. Confirm one of `apps` / `sam-apps` / `applications` / `general`. (I lean `apps` for brevity in 63-char paths.) **Answer** go with `s3access/apps/`
2. **Access-log lockdown level.** Given A1 (no per-bucket or per-tag enforcement possible), is the account + `s3access/*` + optional naming-convention `aws:SourceArn` pattern acceptable as the lockdown, treating `<type>/<bucket-name>` as organizational? Or do you want to invest in per-bucket `aws:SourceArn` statements for the *known/fixed* buckets (artifacts, and any singletons) while leaving project buckets to the convention? **Answer** account + `s3access/*` + naming-convention `aws:SourceArn` pattern is acceptable
3. **CloudFront v2 region strategy.** How should we handle CloudFront's us-east-1 delivery pinning against the regional account-wide bucket? Options: (a) document that CloudFront logging requires the account-wide stack in us-east-1 and send CloudFront logs only to the us-east-1 bucket; (b) allow a separate `S3LogBucketName` override for CloudFront so non-us-east-1 deployments point somewhere valid; (c) something else. This affects the network template design. **Answer** See my answer to Q6. I think option b + c (described in Q6 answer) will do.
4. **"artifacts" scope.** Does Q8's "artifacts" include the **standalone** `template-storage-s3-artifacts.yml`, or only the account-wide artifacts module (which already logs)? (Q4 implies the standalone should also get the import-fallback + `s3access/cf-artifacts/` prefix — confirm.) **Answer** yes, this includes `template-storage-s3-artifacts` As a note, the standalone should still allow legacy CloudFront logging.
5. **Versioning governance (contradiction to flag).** `template-version-control.md` says breaking changes to a PATCH>0 template must spawn a **new MINOR versioned file** with a 24-month support window. Affected versioned templates: `account-wide-infrastructure.yml` (v2.0.2), `template-storage-s3-access-logs.yml`, `template-storage-s3-oac-for-cloudfront.yml`, `template-storage-s3-devops.yml`, `template-storage-s3-artifacts.yml`, `template-network-route53-cloudfront-s3-apigw.yml`. Given Q5 (beta, breakage OK), do you want to **override the steering** and make breaking changes **in place** (version-bump the same files, no parallel v-files), or follow the steering and create new versioned files? I recommend in-place given beta, but this needs your explicit override since it contradicts a workspace rule. **Answer** Yes, override and update in-place.
6. **Legacy CloudFront param removal.** Confirm we fully **remove** `AllowLegacyCloudFrontLogs` (and the bucket's ACL/ownership/public-access-block toggles) rather than keeping it as a deprecated no-op. **Answer:** If the infrastructure is deployed in us-east-2, i really don't want to set up infra in us-east-1 as well. What if we approach this differently by still maintaining `AllowLegacyCloudFrontLogs` but set up a cloudfront-logs-legacy bucket that uses the ACL. V1 can still be used and point to the account-wide legacy bucket, or an alternate bucket (that has ACL) and if the user decides to deploy a network template using v2, then either use the account-wide bucket (if in us-east-1) or have user separately set up an alternate logging bucket in us-east-1. I don't think we need to perform all the checks, but should adequately describe in the parameter description the difference, restrictions, and requirements between v1 and v2 logging

### 8.5 Proposed next step
Once Q1–Q6 above are settled (especially Q3 region strategy and Q5 versioning governance), I'll draft `requirements.md` in EARS form, then `design.md` (exact policy statements, the four `s3access/*` lifecycle rules, the CloudFront v2 delivery resources, the updated Bedrock activation JSON, and a migration/cutover note), then `tasks.md`.

## 9. Round 3 — two-bucket model (v1 + v2 CloudFront coexistence)

Locked from §8 answers: `s3access/apps/` term (A1), account + `s3access/*` + naming-convention `aws:SourceArn` lockdown (A2), standalone `template-storage-s3-artifacts.yml` in scope and it keeps its own legacy CloudFront option (A4), in-place breaking changes / steering override (A5). Q3/Q6 converge on the two-bucket design below.

### 9.1 Decision: keep both CloudFront v1 and v2; isolate the ACL requirement in a second bucket
Instead of removing legacy CloudFront logging, we keep `AllowLegacyCloudFrontLogs` and use it to provision a **dedicated legacy bucket**. This yields two account-wide log buckets:

- **Main logging bucket** (existing `AccessLogBucketRegional`, ACLs **disabled** / `BucketOwnerEnforced`): holds `s3access/*`, `bedrock/*`, and CloudFront **v2** logs (`cloudfront/*`) — the latter only when the account-wide stack is in us-east-1 (see §9.3).
- **Legacy CloudFront bucket** (new, ACLs **enabled** / `BucketOwnerPreferred`), created only when `AllowLegacyCloudFrontLogs = true`: holds CloudFront **v1** standard logs under `cloudfront/`. Works from any region.

Rationale: ACL enablement is a **bucket-level** ObjectOwnership setting — it cannot be scoped to a single prefix — so isolating v1's ACL requirement requires its own bucket. This removes the v1↔Bedrock contradiction without forcing anyone onto us-east-1-only v2.

### 9.2 Recommendation: this is the right call — endorsed
The two-bucket split is cleaner than my earlier "drop v1" proposal and directly serves the maintainer's us-east-2 reality. It also keeps the main bucket's security posture strict (ACLs off) regardless of CloudFront choices.

### 9.3 Hard AWS constraint to design around (more than a doc note)
CloudFront is a global service; its standard-logging-**v2** delivery resources (`AWS::CloudWatchLogs::DeliverySource` for the distribution, plus `DeliveryDestination`/`Delivery`) **can only be created in us-east-1**. Because a CloudFormation stack creates resources in its own region, a network stack deployed in (say) us-east-2 **cannot create working v2 delivery resources at all** — they'd be created in us-east-2 and silently deliver nothing. Implications:
- **v1** (legacy, ACL, inline `Distribution.Logging`) works from **any** region and can target the legacy bucket in the same region. → the practical default for non-us-east-1 (e.g. us-east-2).
- **v2** is only configurable *inside the network template* when that stack is deployed in **us-east-1**; the destination may be the main account-wide bucket (if it too is us-east-1) or a user-supplied us-east-1 ACL-disabled bucket.
- Recommendation: gate the v2 delivery resources behind an `IsUsEast1` condition so we never create non-functional delivery resources, and document the region requirement in the parameter descriptions (per your "describe, don't over-check" guidance). Selecting v2 outside us-east-1 would then simply create nothing for logging + a clear doc warning, rather than broken resources.

### 9.4 Proposed network-template logging interface (for confirmation)
- Parameter `CloudFrontLoggingVersion` with values `none` | `v1` | `v2` (default `v1`, since it works everywhere and matches current behavior).
- Parameter `S3LogBucketName` (existing) as the optional override, with a description spelling out the differing requirements: **v1 →** any-region, ACL-enabled bucket (or leave empty to import the account-wide legacy bucket); **v2 →** us-east-1, ACL-disabled bucket (or leave empty to import the account-wide main bucket when the stack is us-east-1).
- Destination precedence per version: `S3LogBucketName` → account-wide import (legacy bucket for v1 / main bucket for v2) → none.

### 9.5 New account-wide pieces
- New modules: `templates/v2/modules/s3-access-logs/cloudfront-legacy-log-bucket.yml` and `-policy.yml` (ACL-enabled, `BucketOwnerPreferred`, `delivery.logs.amazonaws.com` legacy statement, `cloudfront/` prefix, `LogExpirationInDays` lifecycle), gated on `AllowLegacyCloudFrontLogs`.
- New export: `${OrgPrefix}-CloudFront-Legacy-Log-Bucket-Name` (+ `-Arn`) for producers/network template to import.
- Main bucket policy loses its legacy CloudFront statement (moves to the legacy bucket policy); main bucket ownership is unconditionally enforced.

### 9.6 Sync-steering impact (needs a decision — new Q)
`.kiro/steering/s3-access-logs-module-sync.md` currently requires the account-wide modules and the standalone `template-storage-s3-access-logs.yml` to match except for listed intentional differences. After v0.0.44 the account-wide side diverges substantially (per-prefix lifecycle, Bedrock statement, separate legacy bucket, prefix-scoped policy), while the standalone stays single-bucket with inline legacy ACL toggle (A4). Recommendation: update the sync steering to record these as new intentional differences **or** formally freeze the standalone as deprecated and relax the sync obligation. See §9.7 Q3.

### 9.7 Round 3 clarifying questions
1. **Network logging interface (§9.4):** OK with `CloudFrontLoggingVersion` = `none|v1|v2` (default `v1`) plus a single documented `S3LogBucketName` override? Or would you rather have two explicit override params (one for v1/legacy, one for v2)? **Answer:** This is fine
2. **v2 outside us-east-1 (§9.3):** confirm the approach — gate v2 delivery resources behind an `IsUsEast1` condition (create nothing + doc warning when not us-east-1), rather than attempting cross-region delivery wiring. Agree? **Answer:** Yes, I agree
3. **Sync steering (§9.6):** update `s3-access-logs-module-sync.md` to document the new intentional divergences, or freeze/deprecate the standalone and relax the rule? (I lean: document divergences now, since the standalone still ships.) **Answer:** Please clarify what the divergences are so i can make a final decision. Since we are making a logging bucket, it should still be similar, turn on ACL or off, and have the same lifecycle policies as the main account-wide. **→ Divergence inventory + recommendation in §9.9.**
4. **Legacy bucket default & naming:** keep `AllowLegacyCloudFrontLogs` default `false` (opt-in)? And bucket name `cloudfront-logs-legacy-${AccountId}-${Region}-an` (with optional `${S3BucketNameOrgPrefix}-` prefix), matching the regional `-an` convention — OK? **Answer:** Keep default false and i approve the name.
5. **Legacy bucket lifecycle:** legacy CloudFront logs expire on the shared `LogExpirationInDays`, correct? (Not part of the four `s3access/*` rules, since it's a separate bucket/prefix.) **Answer:** Yes
6. **cf-artifacts sub-type naming:** the `<bucket-name>` in `s3access/cf-artifacts/<bucket-name>/` is somewhat redundant when the type already implies a single account-wide artifacts bucket. Keep `<bucket-name>` for uniformity across all four sub-types, or drop it for the singleton buckets (cf-artifacts)? (I lean keep, for uniform tooling/globbing.) **Answer:** Keep

### 9.8 Next step
With §9.7 settled, the plan is complete enough to draft `requirements.md` (EARS), then `design.md`, then `tasks.md`.

## 9.9 Q3 clarification — divergence inventory (standalone vs account-wide)

First, a note on your comment ("it should still be similar, turn ACL on/off, same lifecycle as main account-wide"). Two things are being conflated, so separating them:

- **The new legacy CloudFront bucket vs the main account-wide bucket** (both live in `account-wide-infrastructure.yml`). These *should* be stylistically consistent — same encryption, versioning, retention approach, Retain policies. The only intentional differences are: the legacy bucket has ACLs **on** (`BucketOwnerPreferred`) and one `cloudfront/` lifecycle rule on `LogExpirationInDays` (per §8 Q5); the main bucket has ACLs **off** and the multi-prefix lifecycle. That consistency is already the plan and is easy to hold.
- **The standalone `template-storage-s3-access-logs.yml` vs the account-wide s3-access-logs modules** — this is what the sync steering governs, and this is where v0.0.44 forces real divergence. Details below.

### What the sync steering assumes today
"The same two S3 access-log resources: an S3 bucket and an S3 bucket policy" — a 1:1 mapping (`AccessLogBucketRegional` + `LoggingBucketPolicy`), identical config except four listed intentional differences (naming drops Prefix/ProjectId; long-form intrinsics; embedded `Condition:` keys; outputs-in-parent).

### Pre-existing intentional differences (already documented — unchanged)
1. Naming: account-wide drops `${Prefix}-${ProjectId}` tokens.
2. Long-form intrinsics in the modules (no `!Sub`/`!Ref`).
3. Module-level `Condition:` keys.
4. Outputs live in the parent with `${OrgPrefix}-` export names.

### NEW divergences introduced by v0.0.44 (the account-wide side only)
| # | Aspect | Standalone (stays as-is) | Account-wide modules (v0.0.44) |
|---|---|---|---|
| D1 | **Bucket count** | One bucket + one policy | **Two** buckets + two policies: main (ACLs off) **plus** a separate `cloudfront-logs-legacy` bucket (ACLs on) |
| D2 | **`AllowLegacyCloudFrontLogs` meaning** | Toggles ACLs **on the single bucket** | Provisions the **separate** legacy bucket; main bucket is unaffected |
| D3 | **Main bucket ownership** | Conditional (`BucketOwnerPreferred` when legacy) | **Always `BucketOwnerEnforced`** (ACLs off), no toggle |
| D4 | **Lifecycle** | One `DeleteOldLogs` rule on `LogExpirationInDays` | Main bucket: **multiple prefix-scoped rules** — `cloudfront/` (v2), four `s3access/*` rules on `S3AccessLogExpirationInDays`, `bedrock/` on `BedrockLargeObjectLogExpirationInDays`. Legacy bucket: one `cloudfront/` rule on `LogExpirationInDays` |
| D5 | **Policy scope** | Whole-bucket `/*` grants | **Prefix-scoped** resources (`.../s3access/*`, `.../cloudfront/*`, `.../bedrock/AWSLogs/.../BedrockModelInvocationLogs/*`) |
| D6 | **Principals** | `logging.s3` + optional legacy `delivery.logs` (v1) | main: `logging.s3` (→`s3access/*`), `delivery.logs` **v2** (→`cloudfront/*`), **`bedrock.amazonaws.com`** (new); legacy bucket: `delivery.logs` **v1** |
| D7 | **Params/conditions** | `LogExpirationInDays`, `AllowLegacyCloudFrontLogs` | adds `S3AccessLogExpirationInDays`, `EnableBedrockLargeObjectLogging`, `BedrockLargeObjectLogExpirationInDays` (+ conditions) |

Net: the "same two resources, identical config" premise no longer holds. D1/D2 alone break the 1:1 resource mapping, and D4–D6 (per-prefix lifecycle, Bedrock, CloudFront v2) are account-wide-only concepts that don't make sense to backport into a single project-scoped bucket (a per-project bucket never receives Bedrock media or the account-wide `cf-artifacts`/`devops`/`apps` aggregation).

### What CAN stay identical (the "still similar" part you want)
Encryption (AES256 + bucket keys), versioning `Suspended`, `Retain`/`UpdateReplace Retain`, the `DenyNonSecureTransportAccess` statement, and the *shape* of the ACL-toggle mechanism (`BlockPublicAcls` + `OwnershipControls`) — these remain common primitives. The legacy account-wide bucket in particular is essentially the standalone's single-bucket pattern with ACLs on and a `cloudfront/`-scoped policy.

### Recommendation (choose one)
- **Option A — Freeze standalone + relax sync rule (recommended).** Leave `template-storage-s3-access-logs.yml` exactly as it is (single project bucket, v1 legacy toggle, single lifecycle, whole-bucket policy). Rewrite `s3-access-logs-module-sync.md` so the standalone is the reference for the **shared primitives only** (D-list items D1–D7 are declared account-wide-only supersets, not drift). Least work, matches its deprecated status, keeps it easy to read.
- **Option B — Modernize standalone to mirror the primitives.** Backport only the safe, in-scope bits (keep the single-bucket ACL toggle, optionally rename its prefix to `s3access/…`) but explicitly NOT Bedrock, NOT v2, NOT the two-bucket split. More churn on a deprecated template; still diverges on D1/D4/D5/D6.
- **Option C — Retire the standalone.** Mark it end-of-life and drop the sync obligation entirely. Cleanest long-term, but removes the per-project option some users may still want.

I recommend **Option A**: the account-wide modules become the living implementation, the standalone stays a frozen, readable reference for the base primitives, and the sync steering is updated to list D1–D7 as intentional, account-wide-only supersets rather than something to reconcile.

### Q3-followup (RESOLVED — Option A)
**Decision: Option A.** The standalone `template-storage-s3-access-logs.yml` is frozen as-is (single project bucket, v1 legacy toggle, single lifecycle, whole-bucket policy). During implementation, `s3-access-logs-module-sync.md` will be updated to: (1) note the account-wide side is now a two-bucket superset, (2) add D1–D7 to the intentional-differences list, and (3) restrict the "keep in sync" obligation to the shared primitives (encryption, versioning, retention policy type, secure-transport deny, ACL-toggle shape).

---

## 10. All questions resolved — proceeding to requirements

Every open question (Rounds 1–3 + Q3 follow-up) is answered. `requirements.md` has been drafted from this plan. `design.md` and `tasks.md` follow.
