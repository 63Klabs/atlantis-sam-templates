---
inclusion: fileMatch
fileMatchPattern: 'templates/v2/{modules/cache-data/*,storage/template-storage-cache-data.yml}'
---

# Cache-Data Module Sync

## Purpose

The standalone template `templates/v2/storage/template-storage-cache-data.yml` and the
`AWS::Include` module snippets under `templates/v2/modules/cache-data/` describe the
**same four Cache-Data resources**: a DynamoDB table, an S3 bucket, an S3 bucket policy,
and a managed Lambda execution-role policy.

The standalone template is the **canonical reference implementation** (prefix + project
scoped) and is intentionally left un-modularized. Because the two are maintained
separately, their resource definitions MUST be kept in sync. This document is the guard
against drift.

> **Important:** The standalone template is the source of truth for resource
> *configuration* (TTL, encryption, lifecycle, IAM actions, statement structure). The
> modules are its intrinsic-normalized, condition-aware counterparts — they must match
> the standalone configuration except for the intentional differences listed below.

## Standalone Logical ID to Module File Mapping

| Standalone logical ID | Resource type | Module file |
|-----------------------|---------------|-------------|
| `CacheDataDynamoDbTable` | `AWS::DynamoDB::Table` | `templates/v2/modules/cache-data/cache-dynamodb-table.yml` |
| `CacheDataS3BucketRegional` | `AWS::S3::Bucket` | `templates/v2/modules/cache-data/cache-s3-bucket.yml` |
| `CacheDataS3BucketPolicy` | `AWS::S3::BucketPolicy` | `templates/v2/modules/cache-data/cache-s3-bucket-policy.yml` |
| `ManagedLambdaExecutionRolePolicy` | `AWS::IAM::ManagedPolicy` | `templates/v2/modules/cache-data/cache-managed-lambda-policy.yml` |

## Intentional Differences (Expected — Do NOT "fix" these)

The modules deliberately diverge from the standalone template in the following ways.
These differences are by design and must be preserved when syncing:

1. **Naming substitution.** The standalone `${ProjectId}` naming token is replaced with
   the literal string `cache-data` in the modules. For example:
   - Table name: standalone `${Prefix}-${ProjectId}-CacheData` →
     module `${Prefix}-cache-data-CacheData`.
   - Bucket name: standalone
     `${S3BucketNameOrgPrefix}-${Prefix}-${ProjectId}-${AWS::AccountId}-${AWS::Region}-an`
     → module `${S3BucketNameOrgPrefix}-${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an`
     (and the no-org-prefix variant likewise).
   - Managed policy name: standalone
     `${Prefix}-${ProjectId}-ManagedLambdaExecutionRolePolicy` →
     module `${Prefix}-cache-data-ManagedLambdaExecutionRolePolicy`.

2. **Long-form intrinsics.** The standalone template uses YAML shorthand tags (`!Sub`,
   `!Ref`, `!If`, `!GetAtt`). The modules use long-form intrinsics only (`Fn::Sub`,
   `Ref`, `Fn::If`, `Fn::GetAtt`) because `AWS::Include` does not support shorthand tags.

3. **Embedded module conditions.** Each module carries a resource-level `Condition:` key
   that the standalone template does not use in the same way:
   - `cache-dynamodb-table.yml`, `cache-s3-bucket.yml`, `cache-s3-bucket-policy.yml`
     carry `Condition: CreateCacheData`.
   - `cache-managed-lambda-policy.yml` carries `Condition: CreateCacheDataManagedPolicy`.

4. **Renamed managed-policy parameter.** The standalone template's
   `CreateManagedLambdaExecutionRolePolicy` parameter is renamed to
   `CreateManagedCacheDataLambdaExecutionRolePolicy` in the consuming
   `prefix-based-infrastructure.yml`, and the module's managed-policy condition is the
   logical AND of `CreateCacheData` and that parameter being `TRUE`.

Everything else — attribute definitions, key schema, TTL, billing mode, retention
policies, public-access block, encryption, lifecycle rules, bucket-policy statements, and
managed-policy statements — MUST match the standalone template verbatim.

## Required Action When Either Side Changes

Any change to the resource configuration on **one** side triggers a review and matching
update of the **other** side **within the same change set**:

1. When editing a `templates/v2/modules/cache-data/*.yml` module, review the
   corresponding resource in `templates/v2/storage/template-storage-cache-data.yml` and
   apply the equivalent change (translating for the intentional differences above).
2. When editing `templates/v2/storage/template-storage-cache-data.yml`, review the
   corresponding module file(s) and apply the equivalent change (translating for the
   intentional differences above).
3. Use the mapping table above to locate the counterpart resource.
4. Confirm that only the intentional differences remain after the sync — no unintended
   configuration drift.
