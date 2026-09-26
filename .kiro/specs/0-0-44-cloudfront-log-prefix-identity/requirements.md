# Requirements Document

**Spec:** v0.0.44 CloudFront Log Prefix Identity Segmentation

## Introduction

The account-wide logging buckets introduced in [0-0-44-bedrock-media-and-log-prefix-segmentation](../0-0-44-bedrock-media-and-log-prefix-segmentation/) organize logs by provider prefix. For S3 server access logs that segmentation goes two levels deep (`s3access/<type>/<bucket-name>/`), so logs from different producers are cleanly separated. CloudFront is the exception: both the legacy (v1) and standard-logging-v2 paths write to a **flat** `cloudfront/` prefix in an **account-wide** bucket, so every distribution in the account interleaves its logs in one location with nothing but log record fields to tell them apart.

This spec adds the deployment identity — `<Prefix>-<ProjectId>-<StageId>` — as a path segment immediately after the `cloudfront/` service prefix, for both logging versions:

```
cloudfront/<Prefix>-<ProjectId>-<StageId>/<log objects>
```

This reverses open design item O2 of the prior spec ("CloudFront v1 uses the flat `cloudfront/` prefix"), which was decided before the account-wide (rather than per-project) nature of the legacy bucket made the cost of flatness apparent.

Scope is deliberately narrow: only the CloudFront prefix changes. The `s3access/<type>/<bucket-name>/` producer prefixes are already adequately segmented and are **not** touched.

### Why no account-wide changes are needed

Verified against the current implementation: the main access log bucket's lifecycle rule and its `AllowCloudFrontV2LogDelivery` policy statement match on `cloudfront/` and `cloudfront/*` respectively, and the legacy bucket's lifecycle rule matches on `cloudfront/`. Because the identity segment is inserted **after** `cloudfront/`, all three continue to match unchanged. No change to `account-wide-infrastructure.yml` or the `s3-access-logs` modules is required.

### Verified AWS behavior

1. **v1** — `DistributionConfig.Logging.Prefix` is arbitrary text prepended to the log file name. Per the [CloudFront standard logging (legacy) file name format](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logging-legacy-s3.html), CloudFront appends a forward slash automatically when the supplied prefix does not end with one, and does not add a second slash when it does. A trailing slash is therefore cosmetic but is the documented recommendation for browsable folders. (Content rephrased for compliance with licensing restrictions.)
2. **v2** — Per the [S3 object key format for V2 deliveries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-V2-S3.html), the optional **destination prefix** appended to the bucket ARN in the delivery destination determines the leading path of delivered objects, and for log types that would otherwise use a default `AWSLogs/<source-account-id>/<service-name>/` path, the destination prefix **replaces** that default path. Delivered object keys therefore begin with the destination prefix. (Content rephrased for compliance with licensing restrictions.)
3. A consequence of (2) is that the existing in-template comment and README text claiming v2 keys land under `cloudfront/AWSLogs/<account>/CloudFront/...` are incorrect and must be corrected as part of this change.
4. `AWS::Logs::DeliveryDestination.DestinationResourceArn` updates require **replacement** of that resource, which in turn replaces the dependent `AWS::Logs::Delivery`. Both are stateless.

---

## Requirements

### Requirement 1: v1 (legacy) log prefix includes the deployment identity

**User Story:** As an operator with several distributions logging to the shared account-wide legacy bucket, I want each distribution's logs under a prefix that names the deployment, so that I can browse, glob, and analyze one application/stage without filtering the whole bucket.

#### Acceptance Criteria

1. WHERE `CloudFrontLoggingVersion` is `v1` AND a destination is resolved, THE network template SHALL set the distribution's `DistributionConfig.Logging.Prefix` to `cloudfront/${Prefix}-${ProjectId}-${StageId}/`.
2. THE prefix SHALL retain `cloudfront/` as its leading segment so that existing lifecycle rules and bucket-policy resource scopes continue to match.
3. THE destination-selection precedence for v1 (`S3LogBucketName` → imported `${OrgPrefix}-CloudFront-Legacy-Log-Bucket-Name` → no logging) SHALL remain unchanged.
4. WHERE no v1 destination is resolved, THE `Logging` property SHALL continue to resolve to `AWS::NoValue`.

### Requirement 2: v2 (standard logging v2) log prefix includes the deployment identity

**User Story:** As an operator using CloudFront standard logging v2 into the account-wide main logging bucket, I want the same identity segmentation as v1, so that the two logging modes produce a consistent layout.

#### Acceptance Criteria

1. WHERE `CloudFrontLoggingVersion` is `v2` AND the v2 delivery resources are created, THE `AWS::Logs::DeliveryDestination.DestinationResourceArn` SHALL use the destination prefix `cloudfront/${Prefix}-${ProjectId}-${StageId}` appended to the destination bucket ARN.
2. THE destination prefix SHALL NOT include a trailing slash, matching the documented destination-prefix form.
3. THE destination-selection precedence for v2 (`S3LogBucketName` → imported `${OrgPrefix}-S3-AccessLog-Bucket-Name` → none) SHALL remain unchanged.
4. THE `IsUsEast1` gating of the v2 delivery resources SHALL remain unchanged.

### Requirement 3: Correct the documented v2 object key layout

**User Story:** As a template user, I want the documentation to describe where v2 log objects actually land, so that I can find them and write correct lifecycle or analytics rules.

#### Acceptance Criteria

1. THE network template's comment describing the v2 delivery resources SHALL state that the destination prefix determines the leading path of delivered objects and replaces the default `AWSLogs/<account>/<service>/` path.
2. THE network template README SHALL NOT claim that v2 keys land under `cloudfront/AWSLogs/<account>/CloudFront/...`.
3. THE corrected documentation SHALL show the resulting layout as `cloudfront/<Prefix>-<ProjectId>-<StageId>/` for both logging versions.

### Requirement 4: `CloudFrontLogPrefix` output reflects the effective prefix

**User Story:** As an operator reading stack outputs, I want the reported log prefix to be accurate and present whenever logging is actually active, so that I can navigate straight to the logs.

#### Acceptance Criteria

1. THE `CloudFrontLogPrefix` output value SHALL be `cloudfront/${Prefix}-${ProjectId}-${StageId}/`.
2. THE `CloudFrontLogPrefix` output SHALL be emitted whenever CloudFront logging is effectively active — that is, when a v1 destination is resolved OR the v2 delivery resources are created — rather than only when `S3LogBucketName` is supplied.
3. WHERE CloudFront logging is not active, THE `CloudFrontLogPrefix` output SHALL NOT be emitted.

### Requirement 5: Test coverage for the prefix

**User Story:** As a maintainer, I want the prefix asserted by fast unit tests, so that a future refactor cannot silently flatten it again.

#### Acceptance Criteria

1. THE unit tests SHALL assert the v1 `Logging.Prefix` value unconditionally, without a type guard that allows the assertion to be skipped when the property is a plain string.
2. THE unit tests SHALL assert that the v2 `DestinationResourceArn` contains the `cloudfront/` segment followed by the `${Prefix}-${ProjectId}-${StageId}` identity.
3. THE unit tests SHALL assert the `CloudFrontLogPrefix` output value and condition per Requirement 4.
4. THE existing property-based test that asserts the v1 prefix SHALL be updated to the new expected value; no new property-based tests SHALL be added.
5. THE full test suite SHALL pass.

### Requirement 6: Versioning and changelog

**User Story:** As a maintainer, I want this change tracked consistently with repository governance.

#### Acceptance Criteria

1. THE network template is at `v0.1.0` (PATCH = 0, development mode, unreleased as part of v0.0.44), so THE version number SHALL NOT be incremented; only the header date SHALL be updated.
2. THE CHANGELOG entry SHALL be added under the existing `## v0.0.44 (unreleased)` section, referencing this spec, and SHALL NOT modify existing entries.

## Non-goals / out of scope

1. Changing the `s3access/<type>/<bucket-name>/` prefixes used by the artifacts, OAC, devops, and standalone artifacts producers. These are already segmented and remain as implemented.
2. Changing the flat `bedrock/` prefix. Bedrock model invocation logging is configured once per account per region and has no project/stage scope.
3. Any change to `account-wide-infrastructure.yml`, the `s3-access-logs` modules, their lifecycle rules, or their bucket policies (verified unnecessary — see Introduction).
4. Changing the `CloudFrontLogBucket` output's `HasLogBucket` condition (it does not report the imported account-wide bucket, but the bucket output is outside this spec's prefix-focused scope).
5. Hive-compatible partitioning or `S3SuffixPath` date/variable partitioning for v2 deliveries.
6. Migrating or relocating log objects already written under the flat `cloudfront/` prefix.

## Constraints and assumptions

1. Existing log objects under the flat `cloudfront/` prefix are left in place and expire under the same lifecycle rule; only newly delivered objects use the new path.
2. Updating an existing v2 stack replaces the `DeliveryDestination` and `Delivery` resources, causing a brief gap in delivery while they are recreated.
3. Updating an existing v1 stack changes the distribution's logging prefix in place; CloudFront distribution updates take 15–20 minutes to propagate.
