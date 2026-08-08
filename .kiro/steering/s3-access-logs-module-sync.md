---
inclusion: fileMatch
fileMatchPattern: 'templates/v2/{modules/s3-access-logs/*,storage/template-storage-s3-access-logs.yml}'
---

# S3 Access-Logs Module Sync

## Purpose

The standalone template `templates/v2/storage/template-storage-s3-access-logs.yml` and the
`AWS::Include` module snippets under `templates/v2/modules/s3-access-logs/` describe the
**same two S3 access-log resources**: an S3 bucket and an S3 bucket policy.

The standalone template is the **canonical reference implementation** (prefix + project
scoped) and is intentionally left un-modularized. Because the two are maintained
separately, their resource definitions MUST be kept in sync. This document is the guard
against drift.

> **Important:** The standalone template is the source of truth for resource
> *configuration* (encryption, lifecycle, public-access block, ownership controls,
> bucket-policy statements). The modules are its intrinsic-normalized, condition-aware,
> account-wide counterparts — they must match the standalone configuration except for the
> intentional differences listed below.

## Standalone Logical ID to Module File Mapping

| Standalone logical ID | Resource type | Module file |
|-----------------------|---------------|-------------|
| `AccessLogBucketRegional` | `AWS::S3::Bucket` | `templates/v2/modules/s3-access-logs/s3-access-log-bucket.yml` |
| `LoggingBucketPolicy` | `AWS::S3::BucketPolicy` | `templates/v2/modules/s3-access-logs/s3-access-log-bucket-policy.yml` |

The consuming parent template (`templates/v2/account/account-wide-infrastructure.yml`)
names the bucket resource `AccessLogBucketRegional` (matching the standalone logical ID so
the policy module's `Ref: AccessLogBucketRegional` resolves) and names the policy resource
`AccessLogBucketPolicy`.

## Intentional Differences (Expected — Do NOT "fix" these)

The modules deliberately diverge from the standalone template in the following ways.
These differences are by design and must be preserved when syncing:

1. **Naming substitution (Prefix and ProjectId removed).** The standalone bucket name is
   `${S3BucketNameOrgPrefix}-${Prefix}-${ProjectId}-access-logs-${AWS::AccountId}-${AWS::Region}-an`
   (or the no-org-prefix variant `${Prefix}-${ProjectId}-access-logs-...`). The modules
   drop the `${Prefix}` and `${ProjectId}` tokens entirely because the account-wide parent
   has neither:
   - With org prefix: `${S3BucketNameOrgPrefix}-access-logs-${AWS::AccountId}-${AWS::Region}-an`
   - Without org prefix: `access-logs-${AWS::AccountId}-${AWS::Region}-an`

2. **Long-form intrinsics.** The standalone template uses YAML shorthand tags (`!Sub`,
   `!Ref`, `!If`, `!GetAtt`, `!Join`). The modules use long-form intrinsics only
   (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::GetAtt`, `Fn::Join`) because `AWS::Include` does not
   support shorthand tags.

3. **Embedded module conditions.** Each module carries a resource-level `Condition:` key
   that the standalone template does not use. Both `s3-access-log-bucket.yml` and
   `s3-access-log-bucket-policy.yml` carry `Condition: EnableS3AccessLogBucket`. The
   condition name intentionally matches the account-wide convention (`EnableS3ArtifactsBucket`,
   etc.) rather than the `Create*` convention used by the cache-data modules.

4. **Outputs live in the parent, with different export names.** The standalone template
   exports `${Prefix}-${ProjectId}-LoggingBucketName` and `-LoggingBucketArn`. Because the
   account-wide parent has no `Prefix`/`ProjectId`, its outputs use the `${OrgPrefix}-`
   convention (for example `${OrgPrefix}-S3-AccessLog-Bucket-Name`). Module files never
   contain outputs.

Everything else — encryption (AES256 with bucket keys), versioning (Suspended), retention
policies (Retain / UpdateReplace Retain), public-access block, lifecycle expiration rule,
ownership controls, legacy CloudFront handling, and bucket-policy statements — MUST match
the standalone template verbatim.

## Required Action When Either Side Changes

Any change to the resource configuration on **one** side triggers a review and matching
update of the **other** side **within the same change set**:

1. When editing a `templates/v2/modules/s3-access-logs/*.yml` module, review the
   corresponding resource in `templates/v2/storage/template-storage-s3-access-logs.yml` and
   apply the equivalent change (translating for the intentional differences above).
2. When editing `templates/v2/storage/template-storage-s3-access-logs.yml`, review the
   corresponding module file(s) and apply the equivalent change (translating for the
   intentional differences above).
3. Use the mapping table above to locate the counterpart resource.
4. Confirm that only the intentional differences remain after the sync — no unintended
   configuration drift.
