# Implementation Plan — Cache-Data Modularization

## Overview

This plan extracts the standalone `template-storage-cache-data.yml` resources into four
reusable `AWS::Include` modules under `templates/v2/modules/cache-data/` and wires them
into `prefix-based-infrastructure.yml` behind opt-in conditions. The standalone template
remains byte-for-byte unchanged; the modules are its intrinsic-normalized, condition-aware
counterparts. Work proceeds module-first (Tasks 1-4), then integrates parameters,
conditions, includes, and outputs into the consuming template (Tasks 5-7), and finishes
with steering, validation, documentation, and changelog updates (Tasks 8-11).

## Tasks

- [x] 1. Create the cache-data module directory and DynamoDB table module
  - Create `templates/v2/modules/cache-data/cache-dynamodb-table.yml` as a single
    resource body (no logical ID, no `Resources:` wrapper)
  - Use long-form intrinsics only; open with the contract comment block declaring
    parameter `Prefix` and condition `CreateCacheData`, plus the KEEP IN SYNC note
  - Set `TableName` to `${Prefix}-cache-data-CacheData`; copy attribute definitions,
    key schema, TTL (`purge_ts`), and `PAY_PER_REQUEST` billing verbatim
  - Preserve `UpdateReplacePolicy: Retain` and `DeletionPolicy: Delete`; add
    `Condition: CreateCacheData`
  - _Requirements: 1_

- [x] 2. Create the cache-data S3 bucket module
  - Create `templates/v2/modules/cache-data/cache-s3-bucket.yml` as a single resource
    body with the contract comment block (params `Prefix`, `S3BucketNameOrgPrefix`,
    `CacheDataPurgeAgeOfCachedBucketObjInDays`; conditions `UseS3BucketNameOrgPrefix`,
    `CreateCacheData`)
  - Bucket name uses `Fn::If` on `UseS3BucketNameOrgPrefix` with the `cache-data`
    literal substituted for the project token
  - Copy `PublicAccessBlockConfiguration`, `BucketEncryption`,
    `BucketNamespace: "account-regional"`, and the `cache`-prefixed
    `LifecycleConfiguration` verbatim; add `Condition: CreateCacheData`
  - _Requirements: 2_

- [x] 3. Create the cache-data S3 bucket policy module
  - Create `templates/v2/modules/cache-data/cache-s3-bucket-policy.yml` as a single
    resource body with the contract comment block (param `Prefix`; condition
    `CreateCacheData`; sibling `CacheDataS3BucketRegional`)
  - Reference the bucket via `Ref: CacheDataS3BucketRegional`; copy the
    `DenyNonSecureTransportAccess` and `AllowLambdaReadWriteDelete` statements verbatim
    (long-form intrinsics); add `Condition: CreateCacheData`
  - _Requirements: 3_

- [x] 4. Create the cache-data managed Lambda execution policy module
  - Create `templates/v2/modules/cache-data/cache-managed-lambda-policy.yml` as a
    single resource body with the contract comment block (params `Prefix`, `RolePath`;
    condition `CreateCacheDataManagedPolicy`; siblings `CacheDataS3BucketRegional`,
    `CacheDataDynamoDbTable`)
  - Set `ManagedPolicyName` to `${Prefix}-cache-data-ManagedLambdaExecutionRolePolicy`;
    copy the three policy statements and `Path: RolePath` verbatim
  - Add `Condition: CreateCacheDataManagedPolicy`
  - _Requirements: 4_

- [x] 5. Add Cache-Data parameters and metadata group to prefix-based-infrastructure.yml
  - Add `EnableCacheData`, `CacheDataPurgeAgeOfCachedBucketObjInDays`, and
    `CreateManagedCacheDataLambdaExecutionRolePolicy` parameters in a new "Cache-Data"
    parameters subsection
  - Add a "Cache-Data" `AWS::CloudFormation::Interface` parameter group ordered after
    existing groups and before "Module Source"
  - Do not add a `ProjectId` parameter
  - _Requirements: 5_

- [x] 6. Add Cache-Data conditions and resource includes to prefix-based-infrastructure.yml
  - Add condition `CreateCacheData` (`EnableCacheData == "true"`) and
    `CreateCacheDataManagedPolicy` (`Fn::And` of `CreateCacheData` and
    `CreateManagedCacheDataLambdaExecutionRolePolicy == "TRUE"`)
  - Add the four `AWS::Include` resources with logical IDs `CacheDataDynamoDbTable`,
    `CacheDataS3BucketRegional`, `CacheDataS3BucketPolicy`,
    `ManagedLambdaExecutionRolePolicy`, each pointing at the corresponding
    `templates/v2/modules/cache-data/*.yml` location
  - Confirm existing `cfn-lint` suppressions (E6101, W2001, W8001) remain sufficient
  - _Requirements: 6_

- [x] 7. Add Cache-Data outputs to prefix-based-infrastructure.yml
  - Add a "Cache-Data" outputs subsection with console links and exports mirroring the
    standalone template; use `CacheData`-prefixed output logical IDs
  - Keep export names identical to the standalone template
    (`${Prefix}-CacheDataDynamoDbTable`, `${Prefix}-CacheDataS3Bucket`,
    `${Prefix}-CacheDataS3BucketArn`, `${Prefix}-CacheDataDynamoDbTableArn`,
    `${Prefix}-CacheDataManagedLambdaExecutionRolePolicy`)
  - Apply `Condition: CreateCacheData` to resource outputs and
    `Condition: CreateCacheDataManagedPolicy` to the managed policy output
  - _Requirements: 7_

- [x] 8. Create the cache-data module sync steering document
  - Create `.kiro/steering/cache-data-module-sync.md` with `inclusion: fileMatch`
    scoped to `templates/v2/modules/cache-data/*` and
    `templates/v2/storage/template-storage-cache-data.yml`
  - Document the sync requirement, the intentional differences (naming substitution,
    long-form intrinsics, embedded conditions, renamed managed-policy parameter), the
    required cross-update action, and a standalone-logical-ID to module-file mapping
  - _Requirements: 8_

- [x] 9. Validate templates and modules
  - Run the repository cfn-lint / pytest linter over `prefix-based-infrastructure.yml`
    and fix any findings
  - Review each module against the module-standards checklist (no logical ID,
    long-form intrinsics, contract comment, correct condition, sibling IDs)
  - Confirm `templates/v2/storage/template-storage-cache-data.yml` is byte-for-byte
    unchanged
  - _Requirements: 10_

- [x] 10. Update documentation
  - Update `templates/v2/modules/README.md` with a Cache-Data Modules section listing
    the four modules and their consuming template
  - Create/update the `prefix-based-infrastructure` documentation under
    `docs/templates/v2/account/` to document the new Cache-Data parameter group,
    resources, conditions, and outputs; preserve any existing blockquotes
  - Cross-reference the modules from
    `docs/templates/v2/storage/template-storage-cache-data-README.md` if helpful
  - _Requirements: 9_

- [x] 11. Update CHANGELOG.md
  - Add an entry under `v0.0.39 (unreleased)` referencing
    `.kiro/specs/0-0-39-cache-data-modularization/`
  - Under Added, list the four new `templates/v2/modules/cache-data/` modules; under
    Changed, note the `prefix-based-infrastructure.yml` cache-data support
  - Do not modify any existing changelog text
  - _Requirements: 9_
  
## Task Dependency Graph

```
1  (DynamoDB table module)
2  (S3 bucket module)
3  (S3 bucket policy module)      depends on 2 (Ref: CacheDataS3BucketRegional)
4  (managed Lambda policy module) depends on 1, 2 (sibling table + bucket)

5  (parameters + metadata group)
6  (conditions + AWS::Include resources) depends on 1, 2, 3, 4, 5
7  (outputs)                             depends on 5, 6

8  (steering sync document)              depends on 1, 2, 3, 4
9  (validate templates and modules)      depends on 1, 2, 3, 4, 5, 6, 7
10 (update documentation)                depends on 5, 6, 7, 8
11 (update CHANGELOG.md)                 depends on 1, 2, 3, 4, 5, 6, 7
```

Critical path: 2 → 3 → 4 → 6 → 7 → 9. Tasks 1 and 2 have no prerequisites and can start
in parallel; Task 5 is independent of the module tasks and can proceed alongside them.

## Notes

- The standalone `templates/v2/storage/template-storage-cache-data.yml` must remain
  byte-for-byte unchanged; Task 9 verifies this explicitly.
- Modules are single resource bodies: no logical ID, no `Resources:` wrapper, long-form
  intrinsics only, and a leading contract comment block declaring required parameters,
  conditions, and sibling logical IDs.
- Intentional differences from the standalone template: naming substitution
  (`cache-data` literal for the project token), long-form intrinsics, embedded
  `Condition` keys, and the renamed managed-policy parameter. These are documented in the
  Task 8 steering file.
- Export names in Task 7 must stay identical to the standalone template so existing
  cross-stack references continue to resolve.
- `_Requirements:_` references map each task to the requirements document; keep them in
  sync if requirements are renumbered.
