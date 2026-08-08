# Implementation Plan — S3 Access-Logs Modularization

## Overview

This plan extracts the standalone `template-storage-s3-access-logs.yml` resources into two
reusable `AWS::Include` modules under `templates/v2/modules/s3-access-logs/` and wires them
into `account-wide-infrastructure.yml` behind an opt-in `EnableS3AccessLogBucket` condition.
The standalone template remains unchanged; the modules are its intrinsic-normalized,
condition-aware, account-wide counterparts. The account-wide artifacts bucket is updated to
use the new access-log bucket as its default logging destination behind a precedence rule
with `S3LogBucketName`.

## Tasks

- [x] 1. Create the s3-access-logs module directory and access-log bucket module
  - Create `templates/v2/modules/s3-access-logs/s3-access-log-bucket.yml` as a single
    resource body (no logical ID, no `Resources:` wrapper)
  - Use long-form intrinsics only; open with the contract comment block declaring params
    `S3BucketNameOrgPrefix`, `LogExpirationInDays`, `AllowLegacyCloudFrontLogs` and
    conditions `UseS3BucketNameOrgPrefix`, `EnableS3AccessLogBucket`,
    `EnableLegacyCloudFrontLogs`, plus the KEEP IN SYNC note
  - Bucket name drops `${Prefix}`/`${ProjectId}`:
    `${S3BucketNameOrgPrefix}-access-logs-${AWS::AccountId}-${AWS::Region}-an` or
    `access-logs-${AWS::AccountId}-${AWS::Region}-an`
  - Copy encryption, versioning, public-access block (legacy toggle), lifecycle, and
    ownership controls verbatim; preserve `DeletionPolicy: Retain` /
    `UpdateReplacePolicy: Retain`; add `Condition: EnableS3AccessLogBucket`
  - _Requirements: 1_

- [x] 2. Create the s3-access-log bucket policy module
  - Create `templates/v2/modules/s3-access-logs/s3-access-log-bucket-policy.yml` as a
    single resource body with the contract comment block (conditions
    `EnableS3AccessLogBucket`, `EnableLegacyCloudFrontLogs`; sibling
    `AccessLogBucketRegional`)
  - Reference the bucket via `Ref: AccessLogBucketRegional`; copy the
    `DenyNonSecureTransportAccess`, `AllowS3LogDelivery`, and conditional
    `AllowCloudFrontLogDelivery` statements verbatim (long-form intrinsics); add
    `Condition: EnableS3AccessLogBucket`
  - _Requirements: 2_

- [x] 3. Add S3 Access Log Bucket parameters and metadata group to account-wide-infrastructure.yml
  - Add `EnableS3AccessLogBucket`, `LogExpirationInDays`, and `AllowLegacyCloudFrontLogs`
    parameters in a new "S3 Access Log Bucket" subsection
  - Add an "S3 Access Log Bucket" `AWS::CloudFormation::Interface` group ordered after
    "S3 Artifacts Bucket" and before "Module Source"
  - _Requirements: 3_

- [x] 4. Add conditions and resource includes to account-wide-infrastructure.yml
  - Add conditions `EnableS3AccessLogBucket` and `EnableLegacyCloudFrontLogs`
  - Add the two `AWS::Include` resources with logical IDs `AccessLogBucketRegional` and
    `AccessLogBucketPolicy`, each pointing at the corresponding
    `templates/v2/modules/s3-access-logs/*.yml` location
  - Confirm existing `cfn-lint` suppressions (E3001, E3005, E6101, W2001, W8001) remain
    sufficient
  - _Requirements: 4_

- [x] 5. Update the artifacts-bucket logging destination precedence
  - In `templates/v2/modules/account-wide/s3-artifacts-bucket.yml`, change
    `LoggingConfiguration` to the nested `Fn::If`: `HasLoggingBucket` →
    `S3LogBucketName`; else `EnableS3AccessLogBucket` → `AccessLogBucketRegional`; else
    `AWS::NoValue`
  - Add `LogFilePrefix: "cf-artifacts/"` to both destination branches
  - Update the module contract comment to declare condition `EnableS3AccessLogBucket` and
    sibling `AccessLogBucketRegional`, and document the precedence
  - Rely on the implicit `Ref: AccessLogBucketRegional` dependency (no fragile `DependsOn`)
  - _Requirements: 5_

- [x] 6. Add S3 Access Log Bucket outputs to account-wide-infrastructure.yml
  - Add `S3AccessLogBucketName` (export `${OrgPrefix}-S3-AccessLog-Bucket-Name`),
    `S3AccessLogBucketArn` (export `${OrgPrefix}-S3-AccessLog-Bucket-Arn`), and
    `S3AccessLogBucketConsole`
  - Apply `Condition: EnableS3AccessLogBucket` to each
  - _Requirements: 6_

- [x] 7. Create the s3-access-logs module sync steering document
  - Create `.kiro/steering/s3-access-logs-module-sync.md` with `inclusion: fileMatch`
    scoped to `templates/v2/modules/s3-access-logs/*` and
    `templates/v2/storage/template-storage-s3-access-logs.yml`
  - Document the sync requirement, intentional differences (dropped Prefix/ProjectId,
    long-form intrinsics, embedded conditions, OrgPrefix exports), the cross-update action,
    and a standalone-logical-ID to module-file mapping
  - _Requirements: 7_

- [x] 8. Update documentation
  - Update `templates/v2/modules/README.md` with an S3 Access-Logs Modules section listing
    the two modules and their consuming template, plus the artifacts-bucket logging
    precedence note
  - Generate/update `docs/templates/v2/account/account-wide-infrastructure-README.md` and
    `docs/templates/v2/account/prefix-based-infrastructure-README.md` documenting
    parameters, resources, conditions, and outputs; preserve existing blockquotes
  - _Requirements: 8_

- [x] 9. Update CHANGELOG.md
  - Add an entry under `v0.0.39 (unreleased)` referencing
    `.kiro/specs/0-0-39-s3-access-logs-modularization/`
  - Under Added, list the two new modules; under Changed, note the
    `account-wide-infrastructure.yml` and `s3-artifacts-bucket.yml` changes
  - Do not modify existing changelog text
  - _Requirements: 8_

- [x] 10. Validate templates and modules
  - Run cfn-lint over `account-wide-infrastructure.yml`; confirm no new findings
  - Review each module against the module-standards checklist
  - Confirm `template-storage-s3-access-logs.yml` is unchanged by this spec
  - Run the storage/account/artifacts unit tests
  - _Requirements: 9_

## Task Dependency Graph

```
1  (access-log bucket module)
2  (access-log bucket policy module)   depends on 1 (Ref: AccessLogBucketRegional)

3  (parameters + metadata group)
4  (conditions + AWS::Include resources) depends on 1, 2, 3
5  (artifacts logging precedence)        depends on 1, 4
6  (outputs)                             depends on 3, 4

7  (steering sync document)              depends on 1, 2
8  (update documentation)                depends on 3, 4, 5, 6, 7
9  (update CHANGELOG.md)                 depends on 1-6
10 (validate templates and modules)      depends on 1-9
```

## Notes

- The standalone `templates/v2/storage/template-storage-s3-access-logs.yml` remains
  unchanged by this spec; Task 10 verifies this.
- Modules are single resource bodies: no logical ID, no `Resources:` wrapper, long-form
  intrinsics only, and a leading contract comment block.
- Intentional differences from the standalone template: dropped `${Prefix}`/`${ProjectId}`
  naming tokens, long-form intrinsics, embedded `EnableS3AccessLogBucket` conditions, and
  parent-side outputs using the `${OrgPrefix}-` convention. Documented in the Task 7
  steering file.
- Artifacts-bucket logging precedence: an explicit `S3LogBucketName` wins; otherwise the
  account-wide access-log bucket (when enabled); otherwise no logging. Logs use the
  `cf-artifacts/` prefix.
