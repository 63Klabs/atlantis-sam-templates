# Requirements Document

S3 Access-Logs Modularization

## Introduction

This feature makes the S3 access-log resources (an S3 bucket and an S3 bucket policy)
available for deployment from the account-level `account-wide-infrastructure.yml`
template, gated by an on/off parameter that mirrors the existing `EnableS3ArtifactsBucket`
/ `EnableApiGwCloudWatchLogs` pattern already used in that template.

The resource definitions are extracted into reusable `AWS::Include` module snippets
stored under `templates/v2/modules/s3-access-logs/`. The existing standalone
`templates/v2/storage/template-storage-s3-access-logs.yml` template is **intentionally
left unchanged** and continues to serve as the canonical reference for the resource
definitions. Because the two are maintained separately, a steering document requires the
standalone template and the s3-access-logs modules to be kept in sync.

Additionally, the account-wide S3 artifacts bucket is wired to use the new access-log
bucket as its server access logging destination, behind a precedence rule with the
existing `S3LogBucketName` parameter.

### Background and Decisions

- `template-storage-s3-access-logs.yml` (v0.0.3) is **not modified** by this spec. It
  remains the prefix + project scoped reference implementation.
- The new modules are consumed **only** by `account-wide-infrastructure.yml` (v0.0.0,
  development mode — edited in place, no version bump).
- In the modules, the `${Prefix}` and `${ProjectId}` naming tokens from the standalone
  template are **dropped entirely**, because `account-wide-infrastructure.yml` has
  neither. This yields a single shared account-wide access log bucket.
- The account-wide parent has no `Prefix`/`ProjectId`, so its outputs use the
  `${OrgPrefix}-` export convention rather than the standalone `${Prefix}-${ProjectId}-`
  names.
- Artifacts-bucket logging precedence (per maintainer direction): an explicitly supplied
  `S3LogBucketName` takes precedence; otherwise the account-wide access log bucket is used
  when `EnableS3AccessLogBucket=true`; otherwise no logging. A redundant `S3LogBucketName`
  set alongside `EnableS3AccessLogBucket=true` is silently ignored.
- Legacy CloudFront logging support is **in scope** (the bucket covers both S3 server
  access logs and legacy CloudFront standard logs).
- Out of scope: any change to the access-log resource *configurations* (copied except for
  the documented naming/intrinsic differences).

### Resources in Scope

| Standalone logical ID | Type | Module file |
|-----------------------|------|-------------|
| `AccessLogBucketRegional` | `AWS::S3::Bucket` | `s3-access-logs/s3-access-log-bucket.yml` |
| `LoggingBucketPolicy` | `AWS::S3::BucketPolicy` | `s3-access-logs/s3-access-log-bucket-policy.yml` |

---

## Glossary

| Term | Definition |
|------|------------|
| **Module** | A reusable `AWS::Include` snippet under `templates/v2/modules/s3-access-logs/` containing a single resource body (no logical ID, no `Resources:` wrapper) consumed via `Fn::Transform: AWS::Include`. |
| **Standalone template** | `templates/v2/storage/template-storage-s3-access-logs.yml` (v0.0.3), the canonical prefix + project scoped reference implementation, left unchanged by this spec. |
| **Access-log resources** | The S3 bucket and S3 bucket policy that make up the access-log resource set. |
| **OrgPrefix** | Upper-case organization identifier used for account-wide export names. |
| **S3BucketNameOrgPrefix** | Optional lower-case organization prefix used in S3 bucket names. |
| **EnableS3AccessLogBucket** | On/off parameter gating creation of the access-log resources, mirroring `EnableS3ArtifactsBucket`. |
| **Long-form intrinsics** | Full-form CloudFormation intrinsic functions (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::GetAtt`, `Fn::Join`) rather than YAML shorthand tags. |
| **Contract comment block** | A leading comment in each module declaring the parent parameters, conditions, and sibling logical IDs the module requires. |

---

## Requirements

## Requirement 1 — S3 Access-Log Bucket Module

**User Story:** As a platform administrator, I want the account-wide S3 access-log bucket
defined as a reusable module, so that it can be included by
`account-wide-infrastructure.yml`.

#### Acceptance Criteria

1. WHEN the module `templates/v2/modules/s3-access-logs/s3-access-log-bucket.yml` is
   authored THEN it SHALL contain a single resource body (no logical ID, no `Resources:`
   wrapper) per the module standards.
2. THE module SHALL use long-form intrinsic functions only — no YAML shorthand tags.
3. THE module SHALL open with a contract comment block declaring the parent parameters
   (`S3BucketNameOrgPrefix`, `LogExpirationInDays`, `AllowLegacyCloudFrontLogs`) and
   conditions (`UseS3BucketNameOrgPrefix`, `EnableS3AccessLogBucket`,
   `EnableLegacyCloudFrontLogs`) it requires, plus the KEEP IN SYNC note.
4. THE bucket name SHALL be
   `${S3BucketNameOrgPrefix}-access-logs-${AWS::AccountId}-${AWS::Region}-an` when
   `UseS3BucketNameOrgPrefix` is true, otherwise
   `access-logs-${AWS::AccountId}-${AWS::Region}-an` (the standalone `${Prefix}` and
   `${ProjectId}` tokens dropped).
5. THE bucket's encryption (AES256 with bucket keys), `BucketNamespace: "account-regional"`,
   versioning (`Suspended`), `PublicAccessBlockConfiguration` (with the
   `EnableLegacyCloudFrontLogs` toggle on `BlockPublicAcls`), `LifecycleConfiguration`
   (`DeleteOldLogs` using `LogExpirationInDays`), and `OwnershipControls` (legacy
   CloudFront toggle) SHALL match the standalone template verbatim.
6. THE module SHALL preserve `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain`.
7. THE module SHALL carry `Condition: EnableS3AccessLogBucket`.

---

## Requirement 2 — S3 Access-Log Bucket Policy Module

**User Story:** As a platform administrator, I want the access-log bucket policy defined
as a reusable module, so that log delivery permissions are applied consistently.

#### Acceptance Criteria

1. THE module `templates/v2/modules/s3-access-logs/s3-access-log-bucket-policy.yml` SHALL
   be a single resource body using long-form intrinsics and a contract comment block that
   declares the required conditions (`EnableS3AccessLogBucket`,
   `EnableLegacyCloudFrontLogs`) and the sibling logical ID it references
   (`AccessLogBucketRegional`).
2. THE policy SHALL reference the bucket via `Ref: AccessLogBucketRegional`.
3. THE policy statements (`DenyNonSecureTransportAccess`, `AllowS3LogDelivery` scoped to
   `aws:SourceAccount = ${AWS::AccountId}`, and the conditional `AllowCloudFrontLogDelivery`
   gated by `EnableLegacyCloudFrontLogs`) SHALL match the standalone template verbatim.
4. THE module SHALL carry `Condition: EnableS3AccessLogBucket`.

---

## Requirement 3 — `account-wide-infrastructure.yml` Parameters and Metadata

**User Story:** As a platform administrator, I want an S3 Access Log Bucket parameter
group, so that I can enable and configure the access-log bucket from a single deployment.

#### Acceptance Criteria

1. THE template SHALL add an `EnableS3AccessLogBucket` parameter (Type String,
   `AllowedValues: ["true","false"]`, `Default: "false"`, with a `ConstraintDescription`).
2. THE template SHALL add a `LogExpirationInDays` parameter (Type Number, `Default: 90`,
   `MinValue: 1`, `MaxValue: 365`) matching the standalone template's definition.
3. THE template SHALL add an `AllowLegacyCloudFrontLogs` parameter (Type String,
   `AllowedValues: ["true","false"]`, `Default: "false"`).
4. THE three new parameters SHALL be grouped under a new `AWS::CloudFormation::Interface`
   parameter group labeled `"S3 Access Log Bucket"`, ordered after `"S3 Artifacts Bucket"`
   and before `"Module Source"`.
5. THE template SHALL reuse the existing `S3BucketNameOrgPrefix` parameter and the
   `UseS3BucketNameOrgPrefix` condition.

---

## Requirement 4 — `account-wide-infrastructure.yml` Conditions and Resources

**User Story:** As a platform administrator, I want the access-log resources created only
when I opt in, so that the stack has no access-log footprint by default.

#### Acceptance Criteria

1. THE template SHALL define a condition `EnableS3AccessLogBucket` equal to
   `!Equals [!Ref EnableS3AccessLogBucket, "true"]`.
2. THE template SHALL define a condition `EnableLegacyCloudFrontLogs` equal to
   `!Equals [!Ref AllowLegacyCloudFrontLogs, "true"]`.
3. THE template SHALL declare logical IDs `AccessLogBucketRegional` (→
   `s3-access-log-bucket.yml`) and `AccessLogBucketPolicy` (→
   `s3-access-log-bucket-policy.yml`), each consuming the corresponding module via
   `Fn::Transform: AWS::Include`.
4. THE bucket logical ID SHALL be `AccessLogBucketRegional` so the policy module's
   `Ref: AccessLogBucketRegional` resolves.
5. WHEN `EnableS3AccessLogBucket` is `"false"` THEN neither access-log resource SHALL be
   created.
6. THE existing `cfn-lint` `ignore_checks` (E3001, E3005, E6101, W2001, W8001) SHALL
   remain sufficient.

---

## Requirement 5 — Artifacts-Bucket Logging Destination Precedence

**User Story:** As a platform administrator, I want the account-wide artifacts bucket to
log to the shared access-log bucket by default, while still allowing an explicit override.

#### Acceptance Criteria

1. THE `s3-artifacts-bucket.yml` module `LoggingConfiguration` SHALL resolve its
   destination by the following precedence:
   1. WHEN `HasLoggingBucket` (S3LogBucketName not empty) THEN log to `S3LogBucketName`.
   2. ELSE WHEN `EnableS3AccessLogBucket` is true THEN log to `AccessLogBucketRegional`.
   3. ELSE no logging (`AWS::NoValue`).
2. WHEN a destination is set THEN the `LogFilePrefix` SHALL be `cf-artifacts/`.
3. WHEN `EnableS3AccessLogBucket=true` and `S3LogBucketName` is also set THEN
   `S3LogBucketName` SHALL win and the redundant value SHALL be silently ignored.
4. THE change SHALL be backward compatible: with `EnableS3AccessLogBucket="false"` (the
   default), behavior SHALL be equivalent to the prior `HasLoggingBucket`-only rule
   (aside from the added `LogFilePrefix`).
5. THE module contract comment SHALL declare the added condition `EnableS3AccessLogBucket`
   and sibling `AccessLogBucketRegional`.
6. THE parent SHALL NOT add a fragile `DependsOn` to a conditionally-absent resource;
   ordering when logging to the access-log bucket SHALL rely on the implicit dependency
   created by `Ref: AccessLogBucketRegional` inside the taken `Fn::If` branch.

---

## Requirement 6 — `account-wide-infrastructure.yml` Outputs

**User Story:** As a platform administrator, I want the access-log bucket outputs surfaced,
so that other stacks and I can reference the created bucket.

#### Acceptance Criteria

1. WHEN `EnableS3AccessLogBucket` is `"true"` THEN the template SHALL output, under an
   `S3 Access Log Bucket` output subsection: `S3AccessLogBucketName` (exported),
   `S3AccessLogBucketArn` (exported), and `S3AccessLogBucketConsole` (console link).
2. THE exported outputs SHALL use export names `${OrgPrefix}-S3-AccessLog-Bucket-Name`
   and `${OrgPrefix}-S3-AccessLog-Bucket-Arn`.
3. EACH access-log output SHALL carry `Condition: EnableS3AccessLogBucket` so no output is
   emitted when the resources are not created.

---

## Requirement 7 — S3 Access-Logs Sync Steering Document

**User Story:** As a maintainer, I want a steering rule that keeps the standalone
access-logs template and the modules in sync, so that the reference template does not
drift from the modules.

#### Acceptance Criteria

1. A new steering document SHALL be created under `.kiro/steering/` scoped to the
   s3-access-logs modules (`templates/v2/modules/s3-access-logs/*`) and the standalone
   template (`templates/v2/storage/template-storage-s3-access-logs.yml`).
2. THE steering document SHALL state that the resource definitions MUST be kept in sync,
   and SHALL document the intentional differences (dropped `${Prefix}`/`${ProjectId}`
   naming tokens, long-form intrinsics, embedded `EnableS3AccessLogBucket` conditions, and
   parent-side outputs using the `${OrgPrefix}-` convention).
3. THE steering document SHALL describe the required cross-update action and include a
   standalone-logical-ID to module-file mapping.

---

## Requirement 8 — Documentation and Changelog

**User Story:** As a user of the template repository, I want documentation and the
changelog updated, so that the new capability is discoverable and traceable.

#### Acceptance Criteria

1. THE `templates/v2/modules/README.md` SHALL be updated with an S3 Access-Logs Modules
   section listing the two new modules and their consuming template, and noting the
   artifacts-bucket logging precedence.
2. THE documentation for `account-wide-infrastructure.yml` and
   `prefix-based-infrastructure.yml` under `docs/templates/v2/account/` SHALL be generated
   (created if absent, updated otherwise), documenting parameters, resources, conditions,
   and outputs. Existing blockquotes and custom content SHALL be preserved.
3. A `CHANGELOG.md` entry SHALL be added under `v0.0.39 (unreleased)`, referencing this
   spec, listing the two new modules (Added) and the `account-wide-infrastructure.yml` /
   `s3-artifacts-bucket.yml` changes (Changed), without modifying existing changelog text.

---

## Requirement 9 — Validation

**User Story:** As a maintainer, I want the changed templates and modules validated, so
that I have confidence the changes deploy correctly.

#### Acceptance Criteria

1. THE `account-wide-infrastructure.yml` template SHALL pass the repository's cfn-lint
   validation (via the existing linter/pytest tooling) with no new findings introduced by
   this change.
2. THE standalone `template-storage-s3-access-logs.yml` SHALL remain unchanged by this
   spec.
3. THE existing storage/account/artifacts unit tests SHALL continue to pass.
