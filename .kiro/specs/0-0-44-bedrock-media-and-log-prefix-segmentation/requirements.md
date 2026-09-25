# Requirements Document

**Spec:** v0.0.44 Bedrock Media Logging + Log Prefix Segmentation & Service Lockdown

## Introduction

This release extends the account-wide logging infrastructure in three connected ways:

1. **Bedrock large-object (media) logging to S3** — route Bedrock model invocation image/video/large-binary payloads (which cannot be delivered to CloudWatch Logs, per the v0.0.43 limitation) to the account-wide logging bucket, filling the gap left by `imageDataDeliveryEnabled`/`videoDataDeliveryEnabled` being forced `false`.
2. **Provider-prefixed log organization + per-prefix lifecycle** — reorganize everything that writes into the account-wide logging bucket under stable provider prefixes (`cloudfront/`, `s3access/<type>/<bucket-name>/`, `bedrock/`) so each prefix can carry its own retention policy.
3. **Per-service bucket-policy lockdown** — scope each writer principal to its own prefix instead of the current whole-bucket grant.

To resolve the incompatibility between CloudFront legacy (v1) standard logging (which requires bucket ACLs enabled) and Bedrock S3 delivery (which requires ACLs disabled), the account-wide stack adopts a **two-bucket model**: a main logging bucket with ACLs disabled (S3 access logs, Bedrock media, and CloudFront v2), and a separate ACL-enabled bucket for CloudFront v1 logs. CloudFront support keeps both v1 and v2 because CloudFront standard logging v2 delivery resources can only be created in us-east-1, which is impractical for non-us-east-1 deployments.

All design decisions were settled during planning; see `PLAN.md` (§8–§10) for the decision record. This is a beta/limited-release product, so breaking changes are made **in place** (version bumps on the same files) rather than via new versioned template files, as an explicit override of `template-version-control.md` approved by the maintainer.

## Glossary

- **Main logging bucket** — the account-wide `AccessLogBucketRegional` (ACLs disabled, `BucketOwnerEnforced`).
- **Legacy CloudFront bucket** — a new account-wide ACL-enabled bucket for CloudFront v1 standard logs.
- **Producer** — any template/bucket that writes logs into a logging bucket (artifacts, OAC origin, devops, CloudFront, Bedrock).
- **CloudFront v1** — legacy standard logging (inline `Distribution.Logging`, ACL delivery via `delivery.logs.amazonaws.com`).
- **CloudFront v2** — standard logging v2 (CloudWatch Logs vended-log delivery resources, no ACLs).

### Prefix taxonomy (normative)

- `cloudfront/` — CloudFront standard logs (v2 in the main bucket; v1 in the legacy bucket).
- `s3access/<type>/<bucket-name>/` — all S3 server access logs, where `<type>` ∈ {`cf-artifacts`, `cloudfront-oac`, `devops`, `apps`} and `<bucket-name>` is the source bucket name.
- `bedrock/` — Bedrock large-object/media invocation logs (Bedrock appends `AWSLogs/{accountId}/BedrockModelInvocationLogs/`).

---

## Requirements

### Requirement 1: Bedrock large-object (media) logging to S3

**User Story:** As an account administrator, I want Bedrock image/video/large-binary invocation payloads delivered to the account-wide logging bucket, so that I can audit model media output that CloudWatch Logs cannot capture.

#### Acceptance Criteria

1. THE account-wide template SHALL provide a parameter `EnableBedrockLargeObjectLogging` (String, `"true"`/`"false"`, default `"false"`) in a "Bedrock Large Object Logs" parameter group.
2. WHERE `EnableBedrockLargeObjectLogging` is `"true"`, THE account-wide template SHALL add a bucket-policy statement granting `bedrock.amazonaws.com` the `s3:PutObject` action on the Bedrock destination bucket, scoped to the resource `<bucket-arn>/bedrock/AWSLogs/${AWS::AccountId}/BedrockModelInvocationLogs/*`.
3. THE Bedrock bucket-policy statement SHALL include the conditions `StringEquals aws:SourceAccount = ${AWS::AccountId}` and `ArnLike aws:SourceArn = arn:${AWS::Partition}:bedrock:${AWS::Region}:${AWS::AccountId}:*`.
4. THE Bedrock delivery destination SHALL be selected with the precedence: explicit `BedrockLargeObjectLogBucketName` (if non-empty) → the main account-wide logging bucket (when `EnableS3AccessLogBucket` is `"true"`) → none.
5. WHERE `EnableBedrockLargeObjectLogging` is `"true"` AND the destination is the account-wide main bucket, THE account-wide template SHALL attach the Bedrock `s3:PutObject` statement to the main bucket policy.
6. WHERE `EnableBedrockLargeObjectLogging` is `"true"` AND `BedrockLargeObjectLogBucketName` is non-empty, THE account-wide template SHALL NOT attempt to modify the external bucket's policy, AND the documentation SHALL state that the administrator must attach the required `bedrock.amazonaws.com` policy to that bucket.
7. THE Bedrock model invocation logging role (from v0.0.43) SHALL remain unchanged (no S3 permissions added), because S3 delivery is authorized by the destination bucket policy, not the role.
8. THE existing CloudWatch text/embedding delivery behavior SHALL remain unchanged (hybrid delivery: text/embedding → CloudWatch, large/binary → S3).

### Requirement 2: Bedrock media activation output

**User Story:** As an account administrator, I want the stack to emit a ready-to-run activation command that includes the S3 large-data-delivery target, so that enabling media logging is a single manual step consistent with v0.0.43.

#### Acceptance Criteria

1. WHERE `EnableBedrockLargeObjectLogging` is `"true"`, THE `BedrockModelInvocationLoggingEnableCommand` output SHALL include `cloudWatchConfig.largeDataDeliveryS3Config` with the resolved bucket name and `keyPrefix` of `bedrock`.
2. WHERE `EnableBedrockLargeObjectLogging` is `"true"`, THE activation output SHALL set `imageDataDeliveryEnabled` and `videoDataDeliveryEnabled` to `true` while keeping `textDataDeliveryEnabled` and `embeddingDataDeliveryEnabled` `true`.
3. WHERE `EnableBedrockLargeObjectLogging` is `"false"`, THE activation output SHALL remain byte-for-byte equivalent to the v0.0.43 output (image/video `false`, no `largeDataDeliveryS3Config`).
4. THE activation SHALL remain a manual, post-deployment CLI step; THE stack SHALL NOT attempt to call `PutModelInvocationLoggingConfiguration`.

### Requirement 3: Bedrock media retention

**User Story:** As an account administrator, I want a dedicated retention control for Bedrock media logs, so that bulky binary payloads can be expired independently of other logs.

#### Acceptance Criteria

1. THE account-wide template SHALL provide a parameter `BedrockLargeObjectLogExpirationInDays` (Number, min 1, max 365, default 90).
2. WHERE `EnableBedrockLargeObjectLogging` is `"true"` AND the destination is the account-wide main bucket, THE main bucket lifecycle SHALL include a rule filtered to `Filter.Prefix: bedrock/` with `ExpirationInDays: !Ref BedrockLargeObjectLogExpirationInDays`.
3. THE `BedrockLargeObjectLogExpirationInDays` parameter SHALL be documented as an **S3 lifecycle** value distinct from the CloudWatch `BedrockInvocationLogExpirationInDays` retention value.

### Requirement 4: Provider-prefix log organization

**User Story:** As an account administrator, I want all logs organized under stable provider prefixes, so that I can apply prefix-based lifecycle and access controls.

#### Acceptance Criteria

1. THE main logging bucket SHALL organize objects under the normative prefix taxonomy (`cloudfront/`, `s3access/<type>/<bucket-name>/`, `bedrock/`).
2. THE `s3access/` prefix SHALL support the sub-types `cf-artifacts`, `cloudfront-oac`, `devops`, and `apps`.
3. THE account-wide artifacts bucket SHALL write server access logs under `s3access/cf-artifacts/<bucket-name>/` (replacing the current `cf-artifacts/` prefix).
4. WHERE a producer bucket is a singleton (for example the account-wide artifacts bucket), THE `<bucket-name>` path segment SHALL be retained for uniform tooling and log globbing.

### Requirement 5: Per-prefix lifecycle rules

**User Story:** As an account administrator, I want each log prefix to have its own lifecycle rule, so that retention can be tuned per log type now and refined later.

#### Acceptance Criteria

1. THE main logging bucket SHALL replace the single `DeleteOldLogs` rule with one lifecycle rule per prefix, each using `Filter.Prefix`.
2. THE `cloudfront/` rule SHALL use `ExpirationInDays: !Ref LogExpirationInDays`.
3. THE main bucket SHALL define four separate `s3access/*` rules — `s3access/cf-artifacts/`, `s3access/cloudfront-oac/`, `s3access/devops/`, `s3access/apps/` — each using `ExpirationInDays: !Ref S3AccessLogExpirationInDays`.
4. THE `bedrock/` rule SHALL use `ExpirationInDays: !Ref BedrockLargeObjectLogExpirationInDays` and SHALL only be present when Bedrock media logging targets the main bucket (per Requirement 3.2).
5. THE account-wide template SHALL provide a parameter `S3AccessLogExpirationInDays` (Number, min 1, max 365, default 180).
6. THE legacy CloudFront bucket lifecycle SHALL use a single `cloudfront/` rule with `ExpirationInDays: !Ref LogExpirationInDays`.

### Requirement 6: Per-service bucket-policy lockdown (main bucket)

**User Story:** As a security-conscious administrator, I want each log-delivery principal restricted to its own prefix, so that a compromised or misconfigured service cannot write across the whole bucket.

#### Acceptance Criteria

1. THE main bucket policy SHALL retain the `DenyNonSecureTransportAccess` statement (deny `s3:*` when `aws:SecureTransport` is false).
2. THE main bucket policy SHALL grant `logging.s3.amazonaws.com` `s3:PutObject` scoped to `<bucket-arn>/s3access/*` with `StringEquals aws:SourceAccount = ${AWS::AccountId}`.
3. THE main bucket `logging.s3.amazonaws.com` statement MAY additionally include an `ArnLike aws:SourceArn` pattern matching the regional bucket naming convention (for example `arn:${AWS::Partition}:s3:::*-an`) to exclude non-conforming source buckets.
4. WHERE CloudFront v2 delivery targets the main bucket, THE main bucket policy SHALL grant `delivery.logs.amazonaws.com` `s3:PutObject` scoped to `<bucket-arn>/cloudfront/*` with `aws:SourceAccount` and `aws:SourceArn` conditions bound to the CloudFront delivery.
5. THE main bucket policy SHALL NOT grant any principal the whole-bucket `<bucket-arn>/*` resource for `s3:PutObject`.
6. IT IS ACKNOWLEDGED that S3 server access log delivery cannot bind the `<bucket-name>` path segment to the actual source bucket, and cannot gate a prefix by source-bucket tag; therefore the `<type>/<bucket-name>` structure is enforced organizationally by each producer's `LogFilePrefix`, not by the destination policy.

### Requirement 7: Main bucket ownership (ACLs disabled)

**User Story:** As a security-conscious administrator, I want the main logging bucket to have ACLs disabled unconditionally, so that it satisfies Bedrock S3 delivery and follows S3 security best practice.

#### Acceptance Criteria

1. THE main logging bucket SHALL set `OwnershipControls` to `BucketOwnerEnforced` unconditionally.
2. THE main logging bucket SHALL set `PublicAccessBlockConfiguration` with `BlockPublicAcls`, `BlockPublicPolicy`, `IgnorePublicAcls`, and `RestrictPublicBuckets` all `true`.
3. THE main logging bucket SHALL NOT contain any `AllowLegacyCloudFrontLogs`-conditional ownership or public-access-block branch.
4. THE main logging bucket SHALL retain AES256 encryption with bucket keys, `VersioningConfiguration: Suspended`, `DeletionPolicy: Retain`, and `UpdateReplacePolicy: Retain`.

### Requirement 8: Legacy CloudFront logging bucket (two-bucket model)

**User Story:** As an administrator deploying outside us-east-1, I want CloudFront v1 logging to keep working via a dedicated ACL-enabled bucket, so that I am not forced into us-east-1-only v2 logging.

#### Acceptance Criteria

1. THE account-wide template SHALL retain the `AllowLegacyCloudFrontLogs` parameter (String, `"true"`/`"false"`, default `"false"`).
2. WHERE `AllowLegacyCloudFrontLogs` is `"true"`, THE account-wide template SHALL provision a separate legacy CloudFront logging bucket and its bucket policy.
3. THE legacy bucket name SHALL be `cloudfront-logs-legacy-${AWS::AccountId}-${AWS::Region}-an`, or `${S3BucketNameOrgPrefix}-cloudfront-logs-legacy-${AWS::AccountId}-${AWS::Region}-an` when an org prefix is supplied.
4. THE legacy bucket SHALL set `OwnershipControls` to `BucketOwnerPreferred` and `BlockPublicAcls` to `false` (ACLs enabled), with `BlockPublicPolicy`, `IgnorePublicAcls`, and `RestrictPublicBuckets` `true`.
5. THE legacy bucket SHALL use AES256 encryption with bucket keys, `VersioningConfiguration: Suspended`, `DeletionPolicy: Retain`, and `UpdateReplacePolicy: Retain`.
6. THE legacy bucket policy SHALL include `DenyNonSecureTransportAccess` and grant `delivery.logs.amazonaws.com` `s3:PutObject` scoped to `<legacy-bucket-arn>/cloudfront/*` with the legacy `StringEquals s3:x-amz-acl = bucket-owner-full-control` condition.
7. WHERE `AllowLegacyCloudFrontLogs` is `"true"`, THE account-wide template SHALL export `${OrgPrefix}-CloudFront-Legacy-Log-Bucket-Name` and `${OrgPrefix}-CloudFront-Legacy-Log-Bucket-Arn`.
8. THE `AllowLegacyCloudFrontLogs` parameter SHALL NOT toggle ACLs on the main logging bucket (this behavior moves to the separate legacy bucket).

### Requirement 9: Producer retrofits (artifacts, OAC, devops, standalone artifacts)

**User Story:** As a template user, I want producer buckets to log to the account-wide bucket automatically under the correct prefix, while still allowing an explicit override, so that logging works with minimal configuration.

#### Acceptance Criteria

1. WHERE a producer template does not already define `OrgPrefix`, THE producer template SHALL add an `OrgPrefix` parameter to enable importing the account-wide logging bucket name.
2. EACH in-scope producer bucket SHALL select its server-access-log destination with the precedence: explicit `S3LogBucketName` (if non-empty) → imported `${OrgPrefix}-S3-AccessLog-Bucket-Name` (when available) → none.
3. THE account-wide artifacts bucket SHALL use `LogFilePrefix: s3access/cf-artifacts/<bucket-name>/`.
4. THE OAC origin bucket (`template-storage-s3-oac-for-cloudfront.yml`) SHALL use `LogFilePrefix: s3access/cloudfront-oac/<bucket-name>/` and the import-fallback precedence.
5. THE devops bucket (`template-storage-s3-devops.yml`) SHALL use `LogFilePrefix: s3access/devops/<bucket-name>/` and the import-fallback precedence.
6. THE standalone artifacts bucket (`template-storage-s3-artifacts.yml`) SHALL use `LogFilePrefix: s3access/cf-artifacts/<bucket-name>/` and the import-fallback precedence.
7. THE cache-data bucket SHALL remain unchanged with no server access logging.

### Requirement 10: CloudFront v1/v2 logging in the network template

**User Story:** As a user of the network template, I want to choose between CloudFront v1 and v2 logging with clear guidance, so that I can log correctly regardless of deployment region.

#### Acceptance Criteria

1. THE network template SHALL provide a parameter `CloudFrontLoggingVersion` with allowed values `none`, `v1`, `v2`, default `v1`.
2. WHERE `CloudFrontLoggingVersion` is `v1`, THE network template SHALL configure the distribution's inline `Logging` block with prefix `cloudfront/` and select its destination with the precedence: explicit `S3LogBucketName` → imported `${OrgPrefix}-CloudFront-Legacy-Log-Bucket-Name` → none.
3. WHERE `CloudFrontLoggingVersion` is `v2` AND the stack region is us-east-1, THE network template SHALL create the CloudWatch Logs vended-log delivery resources (`DeliverySource`, `DeliveryDestination`, `Delivery`) targeting the `cloudfront/` prefix, selecting the destination with the precedence: explicit `S3LogBucketName` → imported `${OrgPrefix}-S3-AccessLog-Bucket-Name` → none.
4. WHERE `CloudFrontLoggingVersion` is `v2` AND the stack region is NOT us-east-1, THE network template SHALL NOT create v2 delivery resources (guarded by an `IsUsEast1` condition), so that no non-functional delivery resources are created.
5. WHERE `CloudFrontLoggingVersion` is `none`, THE network template SHALL configure no CloudFront logging.
6. THE `CloudFrontLoggingVersion` and `S3LogBucketName` parameter descriptions SHALL clearly state the differing requirements: v1 uses an ACL-enabled bucket in any region; v2 requires a us-east-1, ACL-disabled bucket and that the stack be deployed in us-east-1.
7. THE network template SHALL remove the inline `Logging` block only in the v2 branch (v1 continues to use it).

### Requirement 11: Alternate-destination validation

**User Story:** As a template user, I want the stack to reject a configuration where Bedrock media logging is enabled but no destination is available, so that I do not silently lose logs.

#### Acceptance Criteria

1. WHERE `EnableBedrockLargeObjectLogging` is `"true"`, THE account-wide template SHALL enforce (via the CloudFormation `Rules` section) that `EnableS3AccessLogBucket` is `"true"` OR `BedrockLargeObjectLogBucketName` is non-empty.
2. IF the rule in 11.1 is violated, THEN stack creation/update SHALL fail with a descriptive message naming both remediation options.
3. THE account-wide template SHALL provide the parameter `BedrockLargeObjectLogBucketName` (String, S3-bucket-name pattern or empty, default `""`).

### Requirement 12: Versioning and change governance

**User Story:** As a maintainer, I want the breaking changes applied in place with proper version bumps, so that the beta code base stays simple without parallel versioned files.

#### Acceptance Criteria

1. THE breaking changes SHALL be applied in place to the existing template files (no new `-vMAJOR-MINOR` files), as an approved override of `template-version-control.md` for this beta release.
2. EACH modified versioned template SHALL have its header `Version:` and date incremented per its current semantics.
3. THE standalone `template-storage-s3-access-logs.yml` SHALL remain functionally unchanged (frozen) per the Option A decision, aside from any required version/date/documentation housekeeping.
4. THE CHANGELOG SHALL record all changes under the `v0.0.44 (unreleased)` section, categorized, with template version numbers and a spec reference.

### Requirement 13: Sync-steering update (Option A)

**User Story:** As a maintainer, I want the sync steering to reflect that the account-wide modules are now a superset of the standalone, so that future edits are not blocked by an obsolete 1:1 sync rule.

#### Acceptance Criteria

1. THE steering document `.kiro/steering/s3-access-logs-module-sync.md` SHALL be updated to state that the account-wide side is a two-bucket superset of the standalone.
2. THE steering document SHALL add divergences D1–D7 (from `PLAN.md` §9.9) to its intentional-differences list.
3. THE steering document SHALL restrict the "keep in sync" obligation to the shared primitives: encryption, versioning, retention policy type, secure-transport deny statement, and ACL-toggle shape.

### Requirement 14: Documentation

**User Story:** As an end user, I want template documentation updated for the new logging behavior, so that I understand prefixes, retention, CloudFront v1/v2 choices, and Bedrock media activation.

#### Acceptance Criteria

1. THE `docs/admin-ops/bedrock-model-invocation-logging.md` guide SHALL be updated with a section describing S3 large-object/media delivery, the `bedrock/` prefix, the required bucket policy, the SSE-KMS caveat, and the updated activation command (image/video enabled).
2. THE affected template READMEs under `docs/templates/v2/` SHALL be updated for the new/changed parameters, resources, outputs, prefixes, and lifecycle behavior, and category READMEs updated where applicable.
3. THE documentation SHALL explain the two-bucket model and when CloudFront v1 vs v2 applies, including the us-east-1 requirement for v2.
4. THE documentation SHALL state that an externally supplied Bedrock destination bucket (`BedrockLargeObjectLogBucketName`) requires the administrator to attach the `bedrock.amazonaws.com` bucket policy manually.

## Non-goals / out of scope

1. Automated activation of Bedrock model invocation logging (remains a manual CLI step; no custom resource).
2. Creating CloudFront v2 delivery resources for non-us-east-1 stacks, or any cross-region delivery wiring.
3. Attaching bucket policies to externally supplied (`S3LogBucketName` / `BedrockLargeObjectLogBucketName`) buckets.
4. Adding server access logging to the cache-data bucket or to the logging buckets themselves.
5. Per-source-bucket or tag-based enforcement of S3 server-access-log prefixes (not supported by S3 log delivery).
6. Backporting Bedrock, CloudFront v2, per-prefix lifecycle, or the two-bucket split into the standalone `template-storage-s3-access-logs.yml` (frozen per Option A).
7. KMS (SSE-KMS) encryption of the logging buckets (they remain AES256/SSE-S3; KMS support is only noted as a documented caveat).

## Constraints and assumptions

1. CloudFront standard logging v2 delivery resources can only be created in us-east-1 (CloudFront is a global service).
2. S3 server access log delivery authorizes writes via the destination bucket policy conditioned on `aws:SourceAccount` and optionally `aws:SourceArn` (source bucket ARN); no source-tag condition exists.
3. Bedrock S3 delivery is authorized by the destination bucket policy on `bedrock.amazonaws.com` (not the CloudWatch role) and requires bucket ACLs disabled.
4. The account-wide logging bucket is regional; CloudFront v2 logs therefore effectively require a us-east-1 account-wide bucket or a us-east-1 override bucket.
5. Cross-stack imports (`Fn::ImportValue`) require the exporting account-wide stack to be deployed in the same account and region as the importing producer stack.
